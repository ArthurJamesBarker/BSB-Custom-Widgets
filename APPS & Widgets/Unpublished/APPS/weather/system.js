let fetch = require("fetch");
let json = require("json");
let storage = require("storage");
let timer = require("timer");
let time = require("time");

let sys = {
  COLOR_GREEN: "#5DF230",
  COLOR_BG_DARK: "#1D1D1D",
  COLOR_WHITE: "#ffffff",
  COLOR_GRAY: "#808080",
  COLOR_DATE: "#868686",
  COLOR_CONDITION: "#00ff88",

  TEMP_UNIT: "C",

  cities: [
    { name: "London", lat: 51.5, lon: -0.1, tz: 0 },
    { name: "Edinburgh", lat: 56.0, lon: -3.2, tz: 0 },
    { name: "Dublin", lat: 53.3, lon: -6.3, tz: 0 },
    { name: "New York", lat: 40.7, lon: -74.0, tz: -4 },
    { name: "San Francisco", lat: 37.8, lon: -122.4, tz: -7 },
    { name: "Norilsk", lat: 69.3, lon: 88.2, tz: 7 },
    { name: "Singapore", lat: 1.3, lon: 103.8, tz: 8 },
    { name: "Yakutsk", lat: 62.0, lon: 129.7, tz: 9 },
  ],

  config: { city: 1 },
  currentTemp: null,
  currentCode: null,
  forecast: [],
  hourlyTemps: [],
  initHour: 0,
  initUnix: 0,
  loading: true,
  noInternet: false,
  retryTimer: null,

  draw: null,

  weekdays: ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  months: [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ],

  conditionNames: {
    clear: "Clear",
    pcloudy: "Partly cloudy",
    mcloudy: "Mostly cloudy",
    cloudy: "Cloudy",
    humid: "Humid",
    foggy: "Foggy",
    lightrain: "Light rain",
    oshower: "Showers",
    ishower: "Showers",
    rain: "Rain",
    lightsnow: "Light snow",
    snow: "Snow",
    rainsnow: "Rain + snow",
    ts: "Thunderstorm",
    tsrain: "Storm + rain",
  },

  conditionAnims: {
    clear: "w_clear.anim",
    pcloudy: "w_pcloudy.anim",
    mcloudy: "w_mcloudy.anim",
    cloudy: "w_cloudy.anim",
    humid: "w_humid.anim",
    foggy: "w_foggy.anim",
    lightrain: "w_lightrain.anim",
    oshower: "w_oshower.anim",
    ishower: "w_ishower.anim",
    rain: "w_rain.anim",
    lightsnow: "w_rain.anim",
    snow: "w_rain.anim",
    rainsnow: "w_rain.anim",
    ts: "w_rain.anim",
    tsrain: "w_rain.anim",
  },

  localTime: function() {
    return time.localTime();
  },

  unixToLocal: function(utcSec) {
    let c = sys.cities[sys.config.city - 1];
    let local = utcSec + c.tz * 3600;

    let daySec = local % 86400;
    if (daySec < 0) daySec = daySec + 86400;
    let hour = Math.floor(daySec / 3600);
    let minute = Math.floor((daySec % 3600) / 60);
    let second = Math.floor(daySec % 60);

    let z = Math.floor(local / 86400) + 719468;
    let era = Math.floor(z / 146097);
    let doe = z - era * 146097;
    let yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
    let mp = Math.floor((5 * doy + 2) / 153);
    let day = doy - Math.floor((153 * mp + 2) / 5) + 1;
    let month = mp + (mp < 10 ? 3 : -9);
    if (month <= 2) y = y + 1;

    let dse = Math.floor(local / 86400);
    let wd = ((dse + 3) % 7) + 1;
    if (wd <= 0) wd = wd + 7;

    return { year: y, month: month, day: day, hour: hour, minute: minute, second: second, weekday: wd };
  },

  cityTime: function() {
    return sys.unixToLocal(time.now());
  },

  pad2: function(n) {
    if (n < 10) return "0" + str(n);
    return str(n);
  },

  estWidth: function(text) {
    let w = 0;
    for (let i = 0; i < text.length; i++) {
      let c = text[i];
      if (c === " ") w += 2;
      else if (c === ":" || c === ",") w += 2;
      else if (c === "1") w += 3;
      else if (c === "M" || c === "W") w += 5;
      else w += 4;
    }
    return w;
  },

  formatTemp: function(celsius) {
    let v;
    if (sys.TEMP_UNIT === "F") {
      v = Math.floor(celsius * 9 / 5 + 32 + 0.5);
    } else {
      v = Math.floor(celsius + 0.5);
    }
    let sign = v > 0 ? "+" : "";
    return sign + str(v) + "\u00B0C ";
  },

  normCode: function(code) {
    if (code === null || code === undefined) return "";
    let s = str(code).toLowerCase();
    if (s.length > 3 && s.slice(s.length - 3) === "day") return s.slice(0, s.length - 3);
    if (s.length > 5 && s.slice(s.length - 5) === "night") return s.slice(0, s.length - 5);
    return s;
  },

  getCondition: function(code) {
    let key = sys.normCode(code);
    return sys.conditionNames[key] || "Unknown";
  },

  dateToSeconds: function(y, m, d, h) {
    let ya = y;
    let ma = m;
    if (ma <= 2) { ya = ya - 1; ma = ma + 12; }
    let A = Math.floor(ya / 100);
    let B = 2 - A + Math.floor(A / 4);
    let jd = Math.floor(365.25 * (ya + 4716)) + Math.floor(30.6001 * (ma + 1)) + d + B - 1524;
    let unixDays = jd - 2440588;
    return unixDays * 86400 + h * 3600;
  },

  normalizeDate: function(value) {
    let raw = str(value);
    if (raw.length === 8) {
      return raw.slice(0, 4) + "-" + raw.slice(4, 6) + "-" + raw.slice(6, 8);
    }
    return raw;
  },

  buildUrl: function() {
    let c = sys.cities[sys.config.city - 1];
    return "http://www.7timer.info/bin/civil.php"
      + "?lon=" + str(c.lon)
      + "&lat=" + str(c.lat)
      + "&ac=0&unit=metric&output=json&tzshift=0";
  },

  parseWeather: function(body) {
    let data = json.parse(body);
    if (!data || !data.dataseries || data.dataseries.length === 0) {
      return null;
    }

    let initYear = 2026, initMonth = 1, initDay = 1, initHour = 0;
    if (data.init) {
      let s = str(data.init);
      if (s.length >= 10) {
        initYear = Number(s.slice(0, 4));
        initMonth = Number(s.slice(4, 6));
        initDay = Number(s.slice(6, 8));
        initHour = Number(s.slice(8, 10));
      }
    }
    let initUnix = sys.dateToSeconds(initYear, initMonth, initDay, initHour);

    let hourly = [];
    for (let i = 0; i < data.dataseries.length; i++) {
      let item = data.dataseries[i];
      if (!item) continue;
      let tp = Number(item.timepoint);
      if (tp > 72) break;
      let temp = Number(item.temp2m);
      if (temp < -200 || temp > 200) continue;
      hourly.push({
        timepoint: tp,
        temp: temp,
        code: sys.normCode(item.weather),
      });
    }

    if (hourly.length === 0) return null;

    return {
      hourly: hourly,
      initHour: initHour,
      initUnix: initUnix,
    };
  },

  refreshCurrent: function() {
    let pts = sys.hourlyTemps;
    if (!pts || pts.length === 0 || sys.initUnix === 0) return;
    let nowElapsed = (time.now() - sys.initUnix) / 3600;

    let beforeIdx = -1;
    for (let i = 0; i < pts.length; i++) {
      if (pts[i].timepoint <= nowElapsed) beforeIdx = i;
    }

    if (beforeIdx < 0) {
      sys.currentTemp = pts[0].temp;
      sys.currentCode = pts[0].code;
    } else if (beforeIdx >= pts.length - 1) {
      sys.currentTemp = pts[pts.length - 1].temp;
      sys.currentCode = pts[pts.length - 1].code;
    } else {
      let p0 = pts[beforeIdx];
      let p1 = pts[beforeIdx + 1];
      let frac = (nowElapsed - p0.timepoint) / (p1.timepoint - p0.timepoint);
      sys.currentTemp = p0.temp * (1 - frac) + p1.temp * frac;
      sys.currentCode = frac < 0.5 ? p0.code : p1.code;
    }
  },

  stopRetry: function() {
    if (sys.retryTimer !== null) {
      timer.cancel(sys.retryTimer);
      sys.retryTimer = null;
    }
  },

  startRetry: function() {
    if (sys.retryTimer !== null) return;
    sys.retryTimer = timer.every(10, function() {
      sys.fetchWeather();
    });
  },

  fetchWeather: function() {
    sys.loading = true;
    sys.noInternet = false;
    if (sys.draw) sys.draw();

    fetch.get(sys.buildUrl(), function(body, err) {
      sys.loading = false;

      if (err) {
        print("weather fetch error", err);
        if (sys.currentTemp === null) {
          sys.noInternet = true;
          sys.startRetry();
        }
        if (sys.draw) sys.draw();
        return;
      }

      try {
        let result = sys.parseWeather(body);
        if (result) {
          sys.hourlyTemps = result.hourly;
          sys.initHour = result.initHour;
          sys.initUnix = result.initUnix;
          sys.currentTemp = result.hourly[0].temp;
          sys.currentCode = result.hourly[0].code;
          sys.refreshCurrent();
          sys.stopRetry();
        } else {
          print("weather parse: no valid data");
          if (sys.currentTemp === null) {
            sys.noInternet = true;
            sys.startRetry();
          }
        }
      } catch (e) {
        print("weather parse error", e);
        if (sys.currentTemp === null) {
          sys.noInternet = true;
          sys.startRetry();
        }
      }

      if (sys.draw) sys.draw();
    });
  },

  loadConfig: function() {
    if (storage.exists("config.json")) {
      try {
        let raw = storage.read("config.json");
        if (raw) {
          let cfg = json.parse(raw);
          if (cfg && cfg.city) {
            if (cfg.city >= 1 && cfg.city <= sys.cities.length) {
              sys.config.city = cfg.city;
            }
          }
        }
      } catch (e) {}
    }
  },

  saveConfig: function() {
    try {
      storage.write("config.json", json.stringify(sys.config));
    } catch (e) {}
  },
};

sys;

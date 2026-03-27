-- Weather App for Busy Bar
-- 7-day forecast via Open-Meteo API
-- Settings: city (London/Moscow), units (C/F)

local cities = {
    {name = "London", lat = 51.5074, lon = -0.1278, tz = "Europe%2FLondon"},
    {name = "Moscow", lat = 55.7558, lon = 37.6173, tz = "Europe%2FMoscow"},
}

local config = {city = 1, units = 1}
local forecast = {}
local current_temp = nil
local current_code = nil
local day_index = 0
local loading = true
local no_internet = false
local retry_timer = nil

local wmo_icons = {
    [0] = "sun.png",
    [1] = "partly_cloudy.png", [2] = "partly_cloudy.png", [3] = "partly_cloudy.png",
    [45] = "fog.png", [48] = "fog.png",
    [51] = "rain.png", [53] = "rain.png", [55] = "rain.png",
    [56] = "rain.png", [57] = "rain.png",
    [61] = "rain.png", [63] = "rain.png", [65] = "rain.png",
    [66] = "rain.png", [67] = "rain.png",
    [71] = "snow.png", [73] = "snow.png", [75] = "snow.png", [77] = "snow.png",
    [80] = "rain.png", [81] = "rain.png", [82] = "rain.png",
    [85] = "snow.png", [86] = "snow.png",
    [95] = "storm.png", [96] = "storm.png", [99] = "storm.png",
}

local wmo_names = {
    [0] = "Clear sky",
    [1] = "Mostly clear", [2] = "Partly cloudy", [3] = "Overcast",
    [45] = "Fog", [48] = "Rime fog",
    [51] = "Light drizzle", [53] = "Drizzle", [55] = "Dense drizzle",
    [56] = "Freezing drizzle", [57] = "Freezing drizzle",
    [61] = "Light rain", [63] = "Rain", [65] = "Heavy rain",
    [66] = "Freezing rain", [67] = "Freezing rain",
    [71] = "Light snow", [73] = "Snow", [75] = "Heavy snow", [77] = "Snow grains",
    [80] = "Light showers", [81] = "Showers", [82] = "Heavy showers",
    [85] = "Snow showers", [86] = "Heavy snow showers",
    [95] = "Thunderstorm", [96] = "Thunderstorm + hail", [99] = "Thunderstorm + hail",
}

local weekdays = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"}
local months = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}

local function day_of_week(y, m, d)
    local t = {0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4}
    if m < 3 then y = y - 1 end
    return ((y + math.floor(y/4) - math.floor(y/100) + math.floor(y/400) + t[m] + d) % 7) + 1
end

local function get_icon(code)
    return wmo_icons[code] or "partly_cloudy.png"
end

local function get_condition(code)
    return wmo_names[code] or "Unknown"
end

local function fmt_temp(celsius)
    local val = celsius
    if config.units == 2 then
        val = celsius * 9 / 5 + 32
    end
    val = math.floor(val + 0.5)
    local suffix = config.units == 2 and "°F" or "°C"
    if val < 0 then
        return val .. suffix
    else
        return tostring(val) .. suffix
    end
end

local function fmt_date(date_str)
    local y, m, d = date_str:match("(%d+)-(%d+)-(%d+)")
    if y then
        return tonumber(d) .. " " .. months[tonumber(m)]
    end
    return date_str
end

local function get_day_label(idx)
    if not forecast[idx + 1] then return "Day " .. idx end
    local date_str = forecast[idx + 1].date
    local date_fmt = fmt_date(date_str)
    if idx == 0 then return "Today, " .. date_fmt end
    if idx == 1 then return "Tmrw, " .. date_fmt end
    local y, m, d = date_str:match("(%d+)-(%d+)-(%d+)")
    if y then
        local dow = day_of_week(tonumber(y), tonumber(m), tonumber(d))
        return weekdays[dow] .. ", " .. date_fmt
    end
    return date_str
end

local function load_config()
    if busy.storage.exists("config.json") then
        local raw = busy.storage.read("config.json")
        if raw then
            local cfg = busy.json.decode(raw)
            if cfg then
                if cfg.city then config.city = cfg.city end
                if cfg.units then config.units = cfg.units end
            end
        end
    end
end

local function save_config()
    busy.storage.write("config.json", busy.json.encode(config))
end

local function start_retry()
    if retry_timer then return end
    retry_timer = busy.timer.every(3, function()
        local w = busy.wifi.info()
        if w.state == "connected" then
            busy.timer.cancel(retry_timer)
            retry_timer = nil
            no_internet = false
            fetch_weather()
        end
    end)
end

local function draw()
    busy.display.clear()

    if no_internet then
        busy.display.text("No WiFi", {font = "small", align = "center"})
        busy.display.text("Waiting for", {font = "medium", align = "center", y = 20, display = "back"})
        busy.display.text("connection...", {font = "medium", align = "center", y = 34, display = "back"})
        busy.display.show()
        return
    end

    if loading then
        busy.display.text("Loading...", {font = "small", align = "center"})
        busy.display.text("Loading weather...", {font = "medium", align = "center", display = "back"})
        busy.display.show()
        return
    end

    if #forecast == 0 then
        busy.display.text("No data", {font = "small", align = "center"})
        busy.display.text("No weather data", {font = "medium", align = "center", display = "back"})
        busy.display.show()
        return
    end

    local entry = forecast[day_index + 1]
    if not entry then
        busy.display.show()
        return
    end

    local temp_c = entry.temp_max
    if day_index == 0 and current_temp then
        temp_c = current_temp
    end
    local code = entry.code
    if day_index == 0 and current_code then
        code = current_code
    end

    local city_name = cities[config.city].name
    local day_label = get_day_label(day_index)
    local icon_file = get_icon(code)
    local temp_str = fmt_temp(temp_c)
    local gray = "#808080"

    -- Front display: icon + day + city + temp
    busy.display.image(icon_file, {x = 0, y = 0})
    busy.display.text(day_label, {font = "small", x = 18, y = -1, align = "left", color = gray})
    busy.display.text(city_name, {font = "small", x = 71, y = 0, align = "right", color = gray})
    busy.display.text(temp_str, {font = "medium", x = 18, y = 6, align = "left"})

    -- Back display
    busy.display.text(city_name .. " - " .. day_label, {
        font = "medium", align = "center", y = 2, display = "back"
    })
    busy.display.text(get_condition(code), {
        font = "medium", align = "center", y = 16, display = "back"
    })
    local range = fmt_temp(entry.temp_max) .. " / " .. fmt_temp(entry.temp_min)
    busy.display.text(range, {
        font = "medium", align = "center", y = 30, display = "back"
    })

    local nav = (day_index + 1) .. "/7"
    busy.display.text(nav, {
        font = "small", align = "center", y = 48, display = "back", color = gray
    })
    if day_index > 0 then
        busy.display.text("^ prev day", {
            font = "small", align = "center", y = 58, display = "back", color = gray
        })
    end
    if day_index < 6 then
        busy.display.text("v next day", {
            font = "small", align = "center", y = 68, display = "back", color = gray
        })
    end

    busy.display.show()
end

local function fetch_weather()
    local wifi = busy.wifi.info()
    if wifi.state ~= "connected" then
        loading = false
        no_internet = true
        draw()
        start_retry()
        return
    end

    local c = cities[config.city]
    local url = "http://api.open-meteo.com/v1/forecast"
        .. "?latitude=" .. c.lat
        .. "&longitude=" .. c.lon
        .. "&daily=temperature_2m_max,temperature_2m_min,weather_code"
        .. "&current=temperature_2m,weather_code"
        .. "&timezone=" .. c.tz
        .. "&forecast_days=7"

    no_internet = false
    loading = true
    draw()

    busy.fetch.get(url, function(body, err)
        loading = false
        if err then
            if #forecast == 0 then
                no_internet = true
                start_retry()
            end
            draw()
            return
        end

        local data = busy.json.decode(body)
        if not data then
            if #forecast == 0 then
                no_internet = true
                start_retry()
            end
            draw()
            return
        end

        if data.current then
            current_temp = data.current.temperature_2m
            current_code = data.current.weather_code
        end

        forecast = {}
        if data.daily and data.daily.time then
            for i = 1, #data.daily.time do
                table.insert(forecast, {
                    date = data.daily.time[i],
                    temp_max = data.daily.temperature_2m_max[i],
                    temp_min = data.daily.temperature_2m_min[i],
                    code = data.daily.weather_code[i],
                })
            end
        end

        day_index = 0
        draw()
    end)
end

local function open_settings()
    busy.display.clear()
    busy.display.show()

    busy.settings.show({
        {label = "City", options = {"London", "Moscow"}, value = config.city},
        {label = "Units", options = {"Celsius", "Fahrenheit"}, value = config.units},
    }, function(values)
        local changed = (values[1] ~= config.city) or (values[2] ~= config.units)
        config.city = values[1]
        config.units = values[2]
        save_config()
        if changed then
            fetch_weather()
        else
            draw()
        end
    end)
end

load_config()
fetch_weather()

busy.timer.every(1800, function()
    fetch_weather()
end)

busy.input.on("up", "short", function()
    if day_index > 0 then
        day_index = day_index - 1
        draw()
    end
end)

busy.input.on("down", "short", function()
    if day_index < 6 then
        day_index = day_index + 1
        draw()
    end
end)

busy.input.on("ok", "short", function()
    open_settings()
end)

busy.input.on("ok", "long", function()
    open_settings()
end)

busy.input.on("up", "repeat", function()
    if day_index > 0 then
        day_index = day_index - 1
        draw()
    end
end)

busy.input.on("down", "repeat", function()
    if day_index < 6 then
        day_index = day_index + 1
        draw()
    end
end)

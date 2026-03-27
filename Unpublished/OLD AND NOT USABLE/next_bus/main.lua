-- Next Bus (Custom App)
-- Shows upcoming bus arrivals for a single TfL StopPoint.
--
-- IMPORTANT:
-- - Busy Bar Lua can only fetch http:// URLs (no https://).
-- - TfL arrivals are HTTPS-only, so you must run a tiny HTTP proxy on your computer.
--
-- Proxy (run from this folder on your computer, same Wi‑Fi as device):
--   python3 server.py
--
-- Test: curl "http://127.0.0.1:8787/arrivals?stop=490000037S&limit=3"
--
-- Configure: edit DEFAULT_CONFIG below (stop_id, proxy_base). Optional: upload config.json to override.

local DEFAULT_CONFIG = {
    -- Canada Water Bus Station (Stop S) from your link:
    -- https://tfl.gov.uk/bus/arrivals/490000037S/canada-water-bus-station/
    stop_id = "490000037S",

    -- Run the included proxy on your computer, then set this to your computer LAN IP.
    -- Current default: your Mac's IP (change here if it changes).
    proxy_base = "http://10.46.21.104:8787",

    -- How many predictions to request from the proxy
    limit = 8,
}

local config = {}
local arrivals = {}
local loading = true
local no_internet = false
local last_error = nil
local selected = 0
local retry_timer = nil
local scroll_offset = 0
local DEST_VISIBLE = 8   -- chars shown so full line fits on one row (back display ~26 chars)
local LINE_MAX = 26      -- max chars per line to avoid display wrap

local function clamp(n, lo, hi)
    if n < lo then return lo end
    if n > hi then return hi end
    return n
end

local function trim(s, max_len)
    if not s then return "" end
    if #s <= max_len then return s end
    return s:sub(1, max_len - 1) .. "…"
end

-- For long destinations: return 14-char window that scrolls (marquee)
local function scroll_dest(dest, max_len)
    if not dest then return "" end
    dest = tostring(dest)
    if #dest <= max_len then return dest end
    local extended = dest .. "  " .. dest
    local start = (scroll_offset % (#dest + 2)) + 1
    return extended:sub(start, start + max_len - 1)
end

local function load_config()
    -- Allow overriding defaults via config.json upload
    -- Example file contents:
    -- {"stop_id":"490000037S","proxy_base":"http://10.46.21.104:8787","limit":8}
    for k, v in pairs(DEFAULT_CONFIG) do config[k] = v end
    if busy.storage.exists("config.json") then
        local raw = busy.storage.read("config.json")
        if raw then
            local cfg = busy.json.decode(raw)
            if cfg then
                if cfg.stop_id then config.stop_id = tostring(cfg.stop_id) end
                if cfg.proxy_base then config.proxy_base = tostring(cfg.proxy_base) end
                if cfg.limit then config.limit = tonumber(cfg.limit) or config.limit end
            end
        end
    end
    config.limit = clamp(config.limit or 8, 1, 16)
end

local function start_retry(fetch_fn)
    if retry_timer then return end
    retry_timer = busy.timer.every(3, function()
        local w = busy.wifi.info()
        if w.state == "connected" then
            busy.timer.cancel(retry_timer)
            retry_timer = nil
            no_internet = false
            fetch_fn()
        end
    end)
end

local function draw()
    busy.display.clear()

    if no_internet then
        busy.display.text("No WiFi", { font = "small", align = "center" })
        busy.display.text("Waiting for", { font = "medium", align = "center", y = 20, display = "back" })
        busy.display.text("connection...", { font = "medium", align = "center", y = 34, display = "back" })
        busy.display.show()
        return
    end

    if loading then
        busy.display.text("Loading...", { font = "small", align = "center" })
        busy.display.text("Loading…", { font = "medium", align = "center", y = 20, display = "back" })
        busy.display.show()
        return
    end

    if last_error then
        busy.display.text(trim(last_error, 12), { font = "small", align = "center" })
        busy.display.text(trim(last_error, 28), { font = "small", align = "center", y = 20, display = "back" })
        busy.display.show()
        return
    end

    if #arrivals == 0 then
        busy.display.text("No buses", { font = "small", align = "center" })
        busy.display.text("No arrivals", { font = "medium", align = "center", y = 20, display = "back" })
        busy.display.show()
        return
    end

    -- Front (72x16): two buses; one text per line, left part + spaces + mins (mins in fixed column)
    local LEFT_W = 8   -- chars for bus+dest; mins start at column 9
    for i = 0, 1 do
        local row = arrivals[i + 1]
        if not row then break end
        local min = math.floor((row.timeToStation or 0) / 60 + 0.5)
        local line = tostring(row.lineName or "?")
        local d = scroll_dest(row.destinationName, 5)
        local left_part = line .. " " .. d
        if #left_part > LEFT_W then left_part = left_part:sub(1, LEFT_W) end
        local mins = tostring(min) .. "m"
        local full = left_part .. string.rep(" ", LEFT_W - #left_part) .. mins
        if #full > 12 then full = full:sub(1, 12) end
        busy.display.text(full, { font = "small", x = 1, y = i * 8, align = "left" })
    end

    -- Back (160x80): two lines = "Bus - Destination - Time" (destination scrolls if long)
    busy.display.text("Stop " .. config.stop_id, { font = "small", x = 2, y = 0, align = "left", display = "back" })
    busy.display.text("OK: refresh", { font = "small", x = 158, y = 0, align = "right", display = "back" })

    local y0 = 14
    for i = 0, 1 do
        local row = arrivals[selected + 1 + i]
        if not row then break end
        local m = math.floor((row.timeToStation or 0) / 60 + 0.5)
        local l = tostring(row.lineName or "?")
        local d = scroll_dest(row.destinationName, DEST_VISIBLE)
        local line = string.format("%s - %s - %sm", l, d, tostring(m))
        if #line > LINE_MAX then line = line:sub(1, LINE_MAX) end
        busy.display.text(line, { font = "small", x = 2, y = y0 + i * 22, align = "left", display = "back" })
    end

    local a = math.min(selected + 1, #arrivals)
    local b = math.min(selected + 2, #arrivals)
    busy.display.text(tostring(a) .. "-" .. tostring(b) .. "/" .. tostring(#arrivals), { font = "small", x = 80, y = 62, align = "center", display = "back" })

    busy.display.show()
end

local function sort_arrivals(list)
    table.sort(list, function(a, b)
        return (a.timeToStation or 1e9) < (b.timeToStation or 1e9)
    end)
end

local function fetch_arrivals()
    local wifi = busy.wifi.info()
    if wifi.state ~= "connected" then
        loading = false
        no_internet = true
        last_error = nil
        draw()
        start_retry(fetch_arrivals)
        return
    end

    no_internet = false
    loading = true
    last_error = nil
    draw()

    local url = config.proxy_base
        .. "/arrivals?stop=" .. config.stop_id
        .. "&limit=" .. tostring(config.limit or 8)

    local timeout_id = busy.timer.once(8, function()
        if loading then
            loading = false
            last_error = "Timeout 8s"
            draw()
        end
    end)

    busy.fetch.get(url, function(body, err)
        loading = false
        if timeout_id then busy.timer.cancel(timeout_id) end
        if err then
            last_error = "Fetch err"
            arrivals = {}
            draw()
            return
        end

        local data = busy.json.decode(body)
        if not data or type(data) ~= "table" then
            last_error = "Bad JSON"
            arrivals = {}
            draw()
            return
        end

        arrivals = data
        sort_arrivals(arrivals)
        selected = 0
        draw()
    end)
end

load_config()
fetch_arrivals()

-- TfL predictions update about every 30 seconds; keep requests sane
busy.timer.every(30, function()
    fetch_arrivals()
end)

-- Marquee: advance scroll offset so long destinations scroll
busy.timer.every(0.4, function()
    if #arrivals > 0 and not loading and not last_error then
        scroll_offset = scroll_offset + 1
        draw()
    end
end)

busy.input.on("ok", "short", function()
    fetch_arrivals()
end)

busy.input.on("up", "short", function()
    if #arrivals == 0 then return end
    selected = clamp(selected - 1, 0, math.max(0, #arrivals - 2))
    draw()
end)

busy.input.on("down", "short", function()
    if #arrivals == 0 then return end
    selected = clamp(selected + 1, 0, math.max(0, #arrivals - 2))
    draw()
end)

busy.input.on("up", "repeat", function()
    if #arrivals == 0 then return end
    selected = clamp(selected - 1, 0, math.max(0, #arrivals - 2))
    draw()
end)

busy.input.on("down", "repeat", function()
    if #arrivals == 0 then return end
    selected = clamp(selected + 1, 0, math.max(0, #arrivals - 2))
    draw()
end)


-- Audio Player for Busy Bar
-- Plays .snd files (raw PCM 16-bit LE, mono, 44100 Hz)
-- Convert: ffmpeg -i input.mp3 -f s16le -ac 1 -ar 44100 output.snd

local BYTES_PER_SEC = 44100 * 2
local TICK_SEC = 0.25

local tracks = {}
local selected = 1
local playing = false
local volume = 0.7
local elapsed = 0
local cur_duration = 0
local cur_path = ""
local update_timer = nil

local function scan_tracks()
    tracks = {}
    local files = busy.storage.list()
    for _, f in ipairs(files) do
        if not f.is_dir and f.name:match("%.snd$") then
            local dur = math.floor(f.size / BYTES_PER_SEC)
            table.insert(tracks, {
                file = f.name,
                name = f.name:sub(1, -5),
                size = f.size,
                duration = dur
            })
        end
    end
    table.sort(tracks, function(a, b) return a.name < b.name end)
end

local function fmt_time(sec)
    sec = math.floor(sec)
    if sec < 0 then sec = 0 end
    return string.format("%d:%02d", math.floor(sec / 60), sec % 60)
end

local function fmt_vol()
    return tostring(math.floor(volume * 100)) .. "%"
end

local function draw()
    busy.display.clear()

    if #tracks == 0 then
        busy.display.text("No .snd", {
            font = "medium", align = "center", display = "front"
        })
        busy.display.text("No .snd files", {
            font = "medium", align = "center",
            y = 30, display = "back"
        })
        busy.display.show()
        return
    end

    local t = tracks[selected]

    -- Front display: track name + timing
    local prefix = ""
    if playing then prefix = "> " end
    local name_str = prefix .. t.name
    if #name_str > 12 then name_str = name_str:sub(1, 12) end

    busy.display.text(name_str, {
        font = "small", align = "left",
        x = 0, y = 0, display = "front"
    })

    if playing then
        local time_str = fmt_time(elapsed) .. "/" .. fmt_time(cur_duration)
        busy.display.text(time_str, {
            font = "small", align = "left",
            x = 0, y = 9, display = "front"
        })
    else
        local info = fmt_time(t.duration) .. " " .. fmt_vol()
        busy.display.text(info, {
            font = "small", align = "left",
            x = 0, y = 9, display = "front"
        })
    end

    -- Back display
    local back_title = t.name
    if playing then
        back_title = "> " .. back_title
    end
    busy.display.text(back_title, {
        font = "medium", align = "center",
        y = 0, display = "back"
    })

    if playing then
        local time_line = fmt_time(elapsed) .. " / " .. fmt_time(cur_duration)
        busy.display.text(time_line, {
            font = "medium", align = "center",
            y = 14, display = "back"
        })
        busy.display.text("Vol: " .. fmt_vol(), {
            font = "small", align = "center",
            y = 28, display = "back"
        })
    else
        busy.display.text(selected .. "/" .. #tracks .. "  Vol:" .. fmt_vol(), {
            font = "small", align = "center",
            y = 12, display = "back"
        })

        local list_y = 24
        local vis_start = math.max(1, selected - 3)
        local vis_end = math.min(#tracks, vis_start + 5)

        for i = vis_start, vis_end do
            local pfx = "  "
            if i == selected then pfx = "> " end
            local line = pfx .. tracks[i].name
            if #line > 24 then line = line:sub(1, 24) end
            busy.display.text(line, {
                font = "small", align = "left",
                x = 2, y = list_y + (i - vis_start) * 10,
                display = "back"
            })
            busy.display.text(fmt_time(tracks[i].duration), {
                font = "small", align = "right",
                x = 158, y = list_y + (i - vis_start) * 10,
                display = "back"
            })
        end
    end

    busy.display.show()
end

local function stop_playback()
    busy.audio.stop()
    playing = false
    elapsed = 0
    if update_timer then
        busy.timer.cancel(update_timer)
        update_timer = nil
    end
    draw()
end

local function update_tick()
    if not playing then return end

    elapsed = elapsed + TICK_SEC
    if elapsed >= cur_duration then
        stop_playback()
        return
    end

    draw()
end

local function start_playback()
    if #tracks == 0 then return end
    local t = tracks[selected]
    cur_path = "/ext/apps/audio_player/" .. t.file
    cur_duration = t.duration
    elapsed = 0

    busy.audio.volume(volume)
    local ok = busy.audio.play(cur_path)
    if ok then
        playing = true
        update_timer = busy.timer.every(TICK_SEC, update_tick)
    end
    draw()
end

scan_tracks()
busy.audio.volume(volume)
draw()

busy.input.on("ok", "short", function()
    if playing then
        stop_playback()
    else
        start_playback()
    end
end)

busy.input.on("up", "short", function()
    if playing then
        volume = volume + 0.1
        if volume > 1.0 then volume = 1.0 end
        busy.audio.volume(volume)
        draw()
    else
        if selected > 1 then
            selected = selected - 1
            draw()
        end
    end
end)

busy.input.on("down", "short", function()
    if playing then
        volume = volume - 0.1
        if volume < 0.1 then volume = 0.1 end
        busy.audio.volume(volume)
        draw()
    else
        if selected < #tracks then
            selected = selected + 1
            draw()
        end
    end
end)

busy.input.on("up", "repeat", function()
    if playing then
        volume = volume + 0.05
        if volume > 1.0 then volume = 1.0 end
        busy.audio.volume(volume)
        draw()
    else
        if selected > 1 then
            selected = selected - 1
            draw()
        end
    end
end)

busy.input.on("down", "repeat", function()
    if playing then
        volume = volume - 0.05
        if volume < 0.1 then volume = 0.1 end
        busy.audio.volume(volume)
        draw()
    else
        if selected < #tracks then
            selected = selected + 1
            draw()
        end
    end
end)

-- Water Timer (Custom App)
-- Flow:
-- 1) Start screen with a photo; OK starts the countdown
-- 2) Countdown ends with flashing "DRINK" / "REFILL"
-- 3) OK starts the "fill up" animation with a count-up timer
-- 4) When count-up reaches the target, show DONE and OK to restart
--
-- Dial speed-up/slow-down:
-- - During countdown, rotating changes how much time has elapsed (so it ends sooner/later).
-- - During fill, rotating changes the elapsed time (so it reaches 30:00 sooner/later).

local DOWN_FRAMES_DIR = "cup_going_down"
local DOWN_FRAME_COUNT = 30
local ANIM_UP_PATH = "cup_2.anim"

local DEFAULT_DURATION_SECONDS = 30 * 60
local STEP_SECONDS = 60
local MIN_SECONDS = 60
local MAX_SECONDS = 30 * 60

local state = "start" -- start | down | waiting_refill | up | done

local duration_seconds = DEFAULT_DURATION_SECONDS

local tick_timer = nil
local flash_timer = nil
local flash_on = false

local down_total_seconds = 0
local down_elapsed_seconds = 0

local up_total_seconds = 0
local up_elapsed_seconds = 0

local function clamp(n, lo, hi)
    if n < lo then return lo end
    if n > hi then return hi end
    return n
end

local function down_frame_index_from_elapsed(elapsed_seconds)
    -- Frame index advances once per minute (0..29).
    local idx = math.floor(elapsed_seconds / 60)
    return clamp(idx, 0, DOWN_FRAME_COUNT - 1)
end

local function down_frame_path(idx)
    return string.format("%s/cup_going_down_%05d.png", DOWN_FRAMES_DIR, idx)
end

local function format_mmss(total_seconds)
    total_seconds = math.max(0, math.floor(total_seconds + 0.5))
    local mm = math.floor(total_seconds / 60)
    local ss = total_seconds - (mm * 60)
    return string.format("%02d:%02d", mm, ss)
end

local function stop_timer(t)
    if t then busy.timer.cancel(t) end
end

local function cleanup_timers()
    stop_timer(tick_timer)
    tick_timer = nil
    stop_timer(flash_timer)
    flash_timer = nil
end

local function play_anim(path)
    -- Ensure only one back-display widget is active at a time.
    busy.gui.close()
    busy.gui.anim(path)
end

local function render_start()
    busy.display.clear()
    -- Small cup sprite on the front display (16x16), so it doesn't cover timer text.
    busy.display.image(down_frame_path(0), { x = 0, y = 0 })

    -- Back display shows settings/instructions.
    busy.display.text("Water Timer", { font = "small", x = 2, y = 0, align = "left", display = "back" })
    busy.display.text("Start timer", { font = "small", x = 2, y = 16, align = "left", display = "back" })
    busy.display.text("OK: confirm", { font = "small", x = 2, y = 30, align = "left", display = "back" })
    busy.display.text("Dial +/-: time", { font = "small", x = 2, y = 48, align = "left", display = "back" })
    busy.display.text("Target: " .. tostring(math.floor(duration_seconds / 60)) .. " min", { font = "small", x = 2, y = 64, align = "left", display = "back" })
    busy.display.show()
end

local function render_down()
    local remaining = down_total_seconds - down_elapsed_seconds
    busy.display.clear()
    local frame_idx = down_frame_index_from_elapsed(down_elapsed_seconds)
    busy.display.image(down_frame_path(frame_idx), { x = 0, y = 0 })
    -- Place time to the right of the 16x16 cup sprite.
    busy.display.text(format_mmss(remaining), { font = "bold_7", x = 16, y = 0, align = "left" })
    busy.display.show()
end

local function render_waiting_refill()
    busy.display.clear()
    busy.display.image(down_frame_path(DOWN_FRAME_COUNT - 1), { x = 0, y = 0 })
    if flash_on then
        busy.display.text("DRINK", { font = "bold_7", x = 16, y = 0, align = "left" })
        busy.display.text("THEN", { font = "small", x = 16, y = 9, align = "left" })
    else
        busy.display.text("REFILL", { font = "bold_7", x = 16, y = 0, align = "left" })
    end
    busy.display.show()
end

local function render_up()
    busy.display.clear()
    busy.display.text(format_mmss(up_elapsed_seconds), { font = "bold_7", x = 16, y = 0, align = "left" })
    busy.display.text("REFILL", { font = "small", x = 16, y = 9, align = "left" })
    busy.display.show()
end

local function render_done()
    busy.display.clear()
    busy.display.text("DONE", { font = "bold_7", align = "center" })
    busy.display.text("OK: restart", { font = "small", align = "center", y = 10 })
    busy.display.show()
end

local function enter_down_phase()
    cleanup_timers()
    state = "down"
    down_total_seconds = duration_seconds
    down_elapsed_seconds = 0
    busy.gui.close()
    render_down()

    tick_timer = busy.timer.every(1, function()
        if state ~= "down" then return end

        down_elapsed_seconds = down_elapsed_seconds + 1
        if down_elapsed_seconds >= down_total_seconds then
            down_elapsed_seconds = down_total_seconds
            -- Stop countdown tick, switch to flashing prompt.
            stop_timer(tick_timer)
            tick_timer = nil
            state = "waiting_refill"
            busy.gui.close()

            flash_on = false
            render_waiting_refill()
            flash_timer = busy.timer.every(0.5, function()
                if state ~= "waiting_refill" then return end
                flash_on = not flash_on
                render_waiting_refill()
            end)
            return
        end

        render_down()
    end)
end

local function enter_up_phase()
    cleanup_timers()
    state = "up"
    up_total_seconds = down_total_seconds
    up_elapsed_seconds = 0
    play_anim(ANIM_UP_PATH)
    render_up()

    tick_timer = busy.timer.every(1, function()
        if state ~= "up" then return end

        up_elapsed_seconds = up_elapsed_seconds + 1
        if up_elapsed_seconds >= up_total_seconds then
            up_elapsed_seconds = up_total_seconds
            stop_timer(tick_timer)
            tick_timer = nil
            state = "done"
            busy.gui.close()
            render_done()
            return
        end

        render_up()
    end)
end

local function enter_start_phase()
    cleanup_timers()
    state = "start"
    busy.gui.close()
    render_start()
end

local function adjust_time(delta_seconds)
    if delta_seconds == 0 then return end

    if state == "start" then
        duration_seconds = clamp(duration_seconds + delta_seconds, MIN_SECONDS, MAX_SECONDS)
        render_start()
        return
    end

    if state == "down" then
        -- Increasing time means decreasing elapsed (so more seconds remain).
        down_elapsed_seconds = clamp(down_elapsed_seconds - delta_seconds, 0, down_total_seconds)
        -- Countdown uses per-minute PNG frames, so just re-render.
        render_down()
        return
    end

    if state == "up" then
        up_elapsed_seconds = clamp(up_elapsed_seconds + delta_seconds, 0, up_total_seconds)
        play_anim(ANIM_UP_PATH)
        render_up()
        return
    end
end

-- OK: transitions
busy.input.on("ok", "short", function()
    if state == "start" then
        enter_down_phase()
    elseif state == "waiting_refill" then
        enter_up_phase()
    elseif state == "done" then
        enter_start_phase()
    end
end)

-- Dial adjustment (encoder CW/CWW)
busy.input.on("right", "short", function()
    adjust_time(STEP_SECONDS)
end)
busy.input.on("left", "short", function()
    adjust_time(-STEP_SECONDS)
end)
busy.input.on("right", "repeat", function()
    adjust_time(STEP_SECONDS)
end)
busy.input.on("left", "repeat", function()
    adjust_time(-STEP_SECONDS)
end)

-- Initial frame
enter_start_phase()


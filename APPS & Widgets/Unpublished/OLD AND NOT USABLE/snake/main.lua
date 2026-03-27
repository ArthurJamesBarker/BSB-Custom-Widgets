-- Snake: 72x16 front display
-- Game grid 36x8 (snake, food, background); text uses full 72x16 pixel coords
-- Restart only on "ok"

local W, H = 36, 8
local CELL = 2
local DISP_W, DISP_H = 72, 16

local snake = {}
local dir = { dx = 1, dy = 0 }
local food = { x = 0, y = 0 }
local state = "countdown"
local countdown_num = 3
local speed = 1/3
local timer_ref = nil
local blink_ref = nil
local blink_visible = true

local start_timer

local function snake_color(segment_index)
    local n = #snake
    if n <= 1 then return 0, 255, 0 end
    local t = (segment_index - 1) / (n - 1)
    local g = math.floor(255 - (255 - 60) * t)
    return 0, g, 0
end

local function hex(r, g, b)
    r = math.max(0, math.min(255, math.floor(r)))
    g = math.max(0, math.min(255, math.floor(g)))
    b = math.max(0, math.min(255, math.floor(b)))
    return string.format("#%02x%02x%02x", r, g, b)
end

local function random_food()
    local used = {}
    for _, s in ipairs(snake) do
        used[s.x .. "," .. s.y] = true
    end
    local cands = {}
    for x = 0, W - 1 do
        for y = 0, H - 1 do
            if not used[x .. "," .. y] then
                cands[#cands + 1] = { x = x, y = y }
            end
        end
    end
    if #cands == 0 then return end
    local c = cands[math.random(#cands)]
    food.x = c.x
    food.y = c.y
end

local function reset_game()
    snake = {
        { x = 2, y = 4 },
        { x = 1, y = 4 },
        { x = 0, y = 4 },
    }
    dir = { dx = 1, dy = 0 }
    state = "countdown"
    countdown_num = 3
    speed = 1/3
    random_food()
end

local function draw_rect(x, y, w, h, r, g, b)
    local px = x * CELL
    local py = y * CELL
    busy.display.rect(px, py, w, h, { color = hex(r, g, b) })
end

local function draw_game()
    busy.display.image("background.png", { x = 0, y = 0, background = true })

    draw_rect(food.x, food.y, CELL, CELL, 255, 0, 0)

    for i, s in ipairs(snake) do
        local r, g, b = snake_color(i)
        draw_rect(s.x, s.y, CELL, CELL, r, g, b)
    end

    if state == "countdown" then
        busy.display.text(tostring(countdown_num), {
            font = "big", align = "left",
            x = 32, y = 0, display = "front"
        })
    end

    busy.display.show()
end

local function draw_death()
    busy.display.clear()
    busy.display.rect(0, 0, 72, 16, { color = "#6a0000" })
    busy.display.text("you're dead", {
        font = "small", align = "left",
        x = 14, y = 0, display = "front"
    })
    if blink_visible then
        busy.display.text("restart", {
            font = "small", align = "left",
            x = 22, y = 7, display = "front"
        })
    end
    busy.display.show()
end

local function enter_dead()
    if timer_ref then
        busy.timer.cancel(timer_ref)
        timer_ref = nil
    end
    if blink_ref then
        busy.timer.cancel(blink_ref)
        blink_ref = nil
    end
    blink_visible = true
    draw_death()
    blink_ref = busy.timer.every(0.5, function()
        blink_visible = not blink_visible
        draw_death()
    end)
end

local function move_snake()
    if state ~= "play" then return end

    local h = snake[1]
    local nx = h.x + dir.dx
    local ny = h.y + dir.dy

    -- Wrap through walls (only self-collision kills)
    nx = ((nx % W) + W) % W
    ny = ((ny % H) + H) % H

    local will_eat = (nx == food.x and ny == food.y)
    local tail = snake[#snake]

    for _, s in ipairs(snake) do
        if s.x == nx and s.y == ny then
            -- If we're not growing, the tail cell is about to be removed,
            -- so moving into it should be allowed.
            if (not will_eat) and s == tail then
                break
            end

            state = "dead"
            enter_dead()
            return
        end
    end

    table.insert(snake, 1, { x = nx, y = ny })

    if will_eat then
        random_food()
        speed = math.max(0.1, speed * 0.92)
        draw_game()
        start_timer()
    else
        table.remove(snake)
        draw_game()
    end
end

local function countdown_tick()
    if state ~= "countdown" then return end
    countdown_num = countdown_num - 1
    if countdown_num <= 0 then
        state = "play"
        draw_game()
        start_timer()
        return
    end
    draw_game()
end

local function game_tick()
    if state == "countdown" then
        countdown_tick()
    elseif state == "play" then
        move_snake()
    end
end

start_timer = function()
    if timer_ref then busy.timer.cancel(timer_ref) end
    timer_ref = busy.timer.every(state == "countdown" and 1.0 or speed, game_tick)
end

local function stop_blink_timer()
    if blink_ref then
        busy.timer.cancel(blink_ref)
        blink_ref = nil
    end
end

local function on_up()
    if state == "play" then
        local dx, dy = dir.dx, dir.dy
        dir.dx = dy
        dir.dy = -dx
    end
end

local function on_down()
    if state == "play" then
        local dx, dy = dir.dx, dir.dy
        dir.dx = -dy
        dir.dy = dx
    end
end

local function on_ok()
    if state == "dead" then
        stop_blink_timer()
        reset_game()
        draw_game()
        start_timer()
    end
end

reset_game()
draw_game()
start_timer()

busy.input.on("up", "short", on_up)
busy.input.on("down", "short", on_down)
busy.input.on("ok", "short", on_ok)

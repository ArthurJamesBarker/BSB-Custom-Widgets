-- Tetris for Busy Bar (72x16 front display)
-- Field rotated 90°: pieces fall from right (x=71) to left
-- Grid: 22 cols x 8 rows, cell = 2x2 pixels
-- Info panel on the left (27px), game field on the right (44px)

local CELL = 2
local COLS = 22
local ROWS = 8
local FIELD_X = 28
local BASE_SPEED = 0.35
local FAST_SPEED = 0.05

local SCORE_TABLE = {0, 10, 25, 35, 45}

local SHAPES = {
    {{0,0}, {0,1}, {0,2}, {0,3}},
    {{0,0}, {0,1}, {1,0}, {1,1}},
    {{0,0}, {0,1}, {0,2}, {1,1}},
    {{0,1}, {0,2}, {1,0}, {1,1}},
    {{0,0}, {0,1}, {1,1}, {1,2}},
    {{0,0}, {0,1}, {0,2}, {1,0}},
    {{0,0}, {0,1}, {0,2}, {1,2}},
}

local COLORS = {
    "#00cccc",
    "#cccc00",
    "#cc00cc",
    "#00cc00",
    "#cc0000",
    "#cc6600",
    "#0066cc",
}

local board = {}
local cur = nil
local score = 0
local best = 0
local lines = 0
local state = "play"
local timer_ref = nil
local fast_fall = false

local SND_PATH = "/ext/apps/tetris/"

local function play_sound(name)
    busy.audio.play(SND_PATH .. name .. ".snd")
end

local function load_best()
    if busy.storage.exists("best.json") then
        local raw = busy.storage.read("best.json")
        if raw then
            local data = busy.json.decode(raw)
            if data and data.best then
                best = data.best
            end
        end
    end
end

local function save_best()
    busy.storage.write("best.json", busy.json.encode({best = best}))
end

local function update_best()
    if score > best then
        best = score
        save_best()
    end
end

local function get_speed()
    local level = math.floor(lines / 5)
    return math.max(0.08, BASE_SPEED - level * 0.03)
end

local function init_board()
    for c = 0, COLS - 1 do
        board[c] = {}
    end
end

local function piece_blocks(shape, col, row)
    local b = {}
    for i, s in ipairs(shape) do
        b[i] = { col + s[1], row + s[2] }
    end
    return b
end

local function valid_pos(shape, col, row)
    for _, s in ipairs(shape) do
        local c, r = col + s[1], row + s[2]
        if c < 0 or c >= COLS or r < 0 or r >= ROWS then return false end
        if board[c][r] then return false end
    end
    return true
end

local function rotate_shape(shape)
    local new = {}
    for i, b in ipairs(shape) do
        new[i] = { b[2], -b[1] }
    end
    local mc, mr = new[1][1], new[1][2]
    for _, b in ipairs(new) do
        if b[1] < mc then mc = b[1] end
        if b[2] < mr then mr = b[2] end
    end
    for _, b in ipairs(new) do
        b[1] = b[1] - mc
        b[2] = b[2] - mr
    end
    return new
end

local function spawn_piece()
    local idx = math.random(#SHAPES)
    local shape = {}
    for i, b in ipairs(SHAPES[idx]) do
        shape[i] = { b[1], b[2] }
    end
    local max_c, max_r = 0, 0
    for _, b in ipairs(shape) do
        if b[1] > max_c then max_c = b[1] end
        if b[2] > max_r then max_r = b[2] end
    end
    local col = COLS - max_c - 1
    local row = math.floor((ROWS - max_r - 1) / 2)

    if not valid_pos(shape, col, row) then
        state = "gameover"
        update_best()
        play_sound("game-over")
        return
    end
    cur = { shape = shape, color = COLORS[idx], col = col, row = row }
end

local function lock_piece()
    local blocks = piece_blocks(cur.shape, cur.col, cur.row)
    for _, b in ipairs(blocks) do
        board[b[1]][b[2]] = cur.color
    end
    cur = nil
end

local function clear_lines()
    local cleared = 0
    local c = 0
    while c < COLS do
        local full = true
        for r = 0, ROWS - 1 do
            if not board[c][r] then full = false; break end
        end
        if full then
            cleared = cleared + 1
            for cc = c, COLS - 2 do
                board[cc] = board[cc + 1]
            end
            board[COLS - 1] = {}
        else
            c = c + 1
        end
    end
    return cleared
end

local function draw()
    busy.display.clear()

    -- Game field background
    busy.display.rect(FIELD_X, 0, COLS * CELL, ROWS * CELL, { color = "#161616" })

    -- Board cells
    for r = 0, ROWS - 1 do
        local run_start = nil
        local run_color = nil
        for c = 0, COLS - 1 do
            local cell = board[c][r]
            if cell and cell == run_color then
                -- extend
            else
                if run_start then
                    busy.display.rect(
                        FIELD_X + run_start * CELL, r * CELL,
                        (c - run_start) * CELL, CELL,
                        { color = run_color })
                end
                if cell then
                    run_start = c
                    run_color = cell
                else
                    run_start = nil
                    run_color = nil
                end
            end
        end
        if run_start then
            busy.display.rect(
                FIELD_X + run_start * CELL, r * CELL,
                (COLS - run_start) * CELL, CELL,
                { color = run_color })
        end
    end

    -- Current piece
    if cur then
        local blocks = piece_blocks(cur.shape, cur.col, cur.row)
        for _, b in ipairs(blocks) do
            busy.display.rect(
                FIELD_X + b[1] * CELL, b[2] * CELL,
                CELL, CELL,
                { color = cur.color })
        end
    end

    -- Info panel: vertical digits next to vertical label images
    busy.display.image("best.png", {x = 1, y = 1})
    local best_str = tostring(math.floor(best))
    for i = 1, #best_str do
        busy.display.text(best_str:sub(i, i), {font = "small", x = 6, y = (i - 1) * 5 + 1, align = "left", rotation = 90})
    end
    busy.display.image("score.png", {x = 14, y = 1})
    local score_str = tostring(math.floor(score))
    for i = 1, #score_str do
        busy.display.text(score_str:sub(i, i), {font = "small", x = 19, y = (i - 1) * 5 + 1, align = "left", rotation = 90})
    end

    -- Game over overlay
    if state == "gameover" then
        busy.display.rect(FIELD_X + 2, 2, 40, 12, { color = "#000000" })
        busy.display.text("GAME OVER", {
            font = "small", align = "left",
            x = FIELD_X + 6, y = 2
        })
        busy.display.text(tostring(math.floor(score)), {
            font = "small", align = "left",
            x = FIELD_X + 14, y = 9
        })
    end

    -- Back display
    busy.display.text("Tetris", {
        font = "medium", align = "left",
        x = 0, y = 0, display = "back"
    })
    busy.display.text("Score: " .. tostring(math.floor(score)), {
        font = "small", align = "left",
        x = 0, y = 14, display = "back"
    })
    busy.display.text("Best:  " .. tostring(math.floor(best)), {
        font = "small", align = "left",
        x = 0, y = 22, display = "back"
    })
    busy.display.text("Lines: " .. tostring(math.floor(lines)), {
        font = "small", align = "left",
        x = 0, y = 30, display = "back"
    })
    local level = math.floor(lines / 5)
    busy.display.text("Level: " .. tostring(level), {
        font = "small", align = "left",
        x = 0, y = 38, display = "back"
    })

    busy.display.show()
end

local start_timer

local function tick()
    if state ~= "play" or not cur then return end

    if valid_pos(cur.shape, cur.col - 1, cur.row) then
        cur.col = cur.col - 1
    else
        lock_piece()
        local cleared = clear_lines()
        if cleared > 0 then
            lines = lines + cleared
            local pts = SCORE_TABLE[cleared + 1] or (cleared * 10)
            score = score + pts
            play_sound("row-done")
        else
            score = score + 1
            play_sound("mounted")
        end
        update_best()
        spawn_piece()
        if state == "gameover" then
            if timer_ref then busy.timer.cancel(timer_ref); timer_ref = nil end
        else
            start_timer()
        end
    end
    draw()
end

start_timer = function()
    if timer_ref then busy.timer.cancel(timer_ref) end
    local spd = fast_fall and FAST_SPEED or get_speed()
    timer_ref = busy.timer.every(spd, tick)
end

busy.input.on("up", "short", function()
    if cur and state == "play" and valid_pos(cur.shape, cur.col, cur.row - 1) then
        cur.row = cur.row - 1
        draw()
    end
end)

busy.input.on("down", "short", function()
    if cur and state == "play" and valid_pos(cur.shape, cur.col, cur.row + 1) then
        cur.row = cur.row + 1
        draw()
    end
end)

busy.input.on("up", "repeat", function()
    if cur and state == "play" and valid_pos(cur.shape, cur.col, cur.row - 1) then
        cur.row = cur.row - 1
        draw()
    end
end)

busy.input.on("down", "repeat", function()
    if cur and state == "play" and valid_pos(cur.shape, cur.col, cur.row + 1) then
        cur.row = cur.row + 1
        draw()
    end
end)

busy.input.on("ok", "short", function()
    if state == "gameover" then
        init_board()
        score = 0
        lines = 0
        state = "play"
        fast_fall = false
        spawn_piece()
        draw()
        start_timer()
        return
    end
    if cur and state == "play" then
        local ns = rotate_shape(cur.shape)
        if valid_pos(ns, cur.col, cur.row) then
            cur.shape = ns
            play_sound("rotate")
            draw()
        end
    end
end)

busy.input.on("ok", "long", function()
    if state == "play" then
        fast_fall = true
        start_timer()
    end
end)

busy.input.on("ok", "release", function()
    if fast_fall then
        fast_fall = false
        if state == "play" then start_timer() end
    end
end)

load_best()
init_board()
spawn_piece()
draw()
start_timer()

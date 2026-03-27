-- Battery Level (Custom App)
-- Shows one of five battery-level images. Scroll wheel (up/down) cycles through states 1..5.
-- Back (short press) exits to APPS menu.

local NUM_STATES = 5
local current = 1

local function draw()
    busy.display.clear()
    local path = current .. ".png"
    busy.display.image(path, { x = 0, y = 0 })
    busy.display.show()
end

-- Up (scroll forward): next state, wrap 5 -> 1
busy.input.on("up", "short", function()
    current = (current % NUM_STATES) + 1
    draw()
end)

-- Down (scroll back): previous state, wrap 1 -> 5
busy.input.on("down", "short", function()
    current = current - 1
    if current < 1 then current = NUM_STATES end
    draw()
end)

-- Initial frame
draw()

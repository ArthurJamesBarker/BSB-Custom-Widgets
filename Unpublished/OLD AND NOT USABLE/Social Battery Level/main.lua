-- Social Battery Level (Custom App)
-- Displays one of five battery title images only (N_Battery.png).
-- Scroll wheel changes level 1..5.
-- Back (short press) exits to APPS menu.

local NUM_STATES = 5
local current = 1

local function draw()
    busy.display.clear()
    busy.display.image(current .. "_Battery.png", { x = 0, y = 0 })
    busy.display.show()
end

draw()

-- Up (scroll forward): next level, wrap 5 -> 1
busy.input.on("up", "short", function()
    current = (current % NUM_STATES) + 1
    draw()
end)

-- Down (scroll back): previous level, wrap 1 -> 5
busy.input.on("down", "short", function()
    current = current - 1
    if current < 1 then current = NUM_STATES end
    draw()
end)

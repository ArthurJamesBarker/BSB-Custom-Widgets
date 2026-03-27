local DEFAULT = 99
local count = DEFAULT
local confetti_id = nil

if busy.storage.exists("count.txt") then
    local saved = busy.storage.read("count.txt")
    local n = tonumber(saved)
    if n and n >= 0 and n <= DEFAULT then
        count = n
    end
end

local function clamp(v, lo, hi)
    return math.max(lo, math.min(hi, v))
end

local function lerp(a, b, t)
    return math.floor(a + (b - a) * t + 0.5)
end

local function hex(r, g, b)
    return string.format("#%02x%02x%02x",
        clamp(math.floor(r), 0, 255),
        clamp(math.floor(g), 0, 255),
        clamp(math.floor(b), 0, 255))
end

local function update_led()
    local t = count / DEFAULT
    local r = lerp(200, 0, t)
    local g = lerp(0, 160, t)
    busy.led.set(r, g, 0)
end

local function draw()
    -- Don't call clear() — canvas redraws over the top without a black flash
    -- Background gradient: green (#076a00) at 99 → red (#6a0000) at 0
    -- 18 strips across 72px (4px each), fading left→right
    local t = count / DEFAULT
    local br = lerp(106, 7, t)
    local bg = lerp(0, 106, t)
    local STEPS = 18
    local sw = 72 / STEPS
    for i = 0, STEPS - 1 do
        local fade = (STEPS - 1 - i) / (STEPS - 1)
        busy.display.rect(
            math.floor(i * sw), 0,
            math.ceil(sw), 16,
            {color = hex(lerp(0, br, fade), lerp(0, bg, fade), 0)}
        )
    end

    busy.display.image("plashka2.png", {x = 1, y = 0})

    local s = tostring(count)
    busy.display.text(s, {font = "big", align = "left", x = 4, y = 1})
    busy.display.text("BRAIN", {font = "small", align = "left", x = 25, y = 0})
    busy.display.text("CELLS", {font = "small", align = "left", x = 48, y = 0})
    busy.display.text("LEFT",  {font = "small", align = "left", x = 25, y = 8})

    busy.display.text(s, {font = "big", align = "center", display = "back", y = 5})
    busy.display.text("BRAIN CELLS LEFT", {font = "small", align = "center", display = "back", y = 40})
    busy.display.text("hold = reset to 99", {font = "small", align = "center", display = "back", y = 55})

    busy.display.show()
    update_led()
end

local function play_confetti()
    if confetti_id then
        busy.lottie.stop(confetti_id)
        confetti_id = nil
    end
    confetti_id = busy.lottie.play("white-confetti.json", {
        x = 0, y = 0,
        loop = false,
        on_complete = function()
            confetti_id = nil
        end
    })
end

local function do_click()
    if count <= 0 then return end
    count = count - 1
    busy.storage.write("count.txt", tostring(count))
    draw()
    if count == 0 then
        play_confetti()
    end
end

local function do_reset()
    if confetti_id then
        busy.lottie.stop(confetti_id)
        confetti_id = nil
    end
    count = DEFAULT
    busy.storage.write("count.txt", tostring(count))
    draw()
end

draw()

local keys = {"ok", "up", "down", "start"}
for _, key in ipairs(keys) do
    busy.input.on(key, "short", do_click)
    busy.input.on(key, "long", do_reset)
end

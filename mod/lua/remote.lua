-- Remote control for BizHawk. Polls a command file once per frame so the game can be
-- driven from outside the emulator (see tools/mod/emu.sh).
--
-- Directory: environment variable S2_REMOTE_DIR. Write commands to <dir>/cmd.txt, one
-- per line; when all have run, <dir>/done.txt holds their output.
--
--   press <buttons> [frames]   hold e.g. "A" or "A+DPad D" (default 4 frames), then release
--   hold <buttons> <frames> [name]   hold, and screenshot to <name>.png while held
--   stick <x> <y> [frames]     hold the analog stick (-127..127)
--   wait <frames>
--   shot <name>                screenshot to <dir>/<name>.png
--   save <name> / load <name>  savestate <dir>/<name>.State
--   read <hex addr> <len>      hex dump of RDRAM at a 0x80xxxxxx address
--   dump <hex addr> <len> <name>  raw bytes to <dir>/<name>.bin
--   find <hex bytes>           addresses of every occurrence in RDRAM
--   u32 <hex addr>             one big-endian word
--   write <hex addr> <hex bytes>
--   turbo on|off               unthrottled emulation
--   frame                      print the frame counter
--   eval <lua>                 run a Lua chunk inside the emulator and print its results
--   exit                       close the emulator

local dir = os.getenv("S2_REMOTE_DIR")
assert(dir, "S2_REMOTE_DIR is not set")
local cmd_path = dir .. "\\cmd.txt"
local done_path = dir .. "\\done.txt"

local RDRAM = "RDRAM"
local out = {}

local function log(s) out[#out + 1] = s end

local function to_offset(text)
    local addr = tonumber(text, 16)
    assert(addr, "bad address: " .. tostring(text))
    if addr >= 0x80000000 then addr = addr - 0x80000000 end
    return addr
end

local function advance(frames, pad, analog)
    for _ = 1, frames do
        if pad then joypad.set(pad, 1) end
        if analog then joypad.setanalog(analog, 1) end
        emu.frameadvance()
    end
end

local function hex_bytes(text)
    local bytes = {}
    for b in text:gmatch("%x%x") do bytes[#bytes + 1] = tonumber(b, 16) end
    return bytes
end

local commands = {}

function commands.press(args)
    local frames = tonumber(args[#args])
    local last = frames and #args - 1 or #args
    local pad = {}
    for name in table.concat(args, " ", 1, last):gmatch("[^+]+") do
        pad[name:match("^%s*(.-)%s*$")] = true
    end
    advance(frames or 4, pad)
    advance(2)
end

-- hold <buttons> <frames> [name]: like press, but screenshots before letting go.
function commands.hold(args)
    local at = 1
    while args[at] and not tonumber(args[at]) do at = at + 1 end
    local pad = {}
    for name in table.concat(args, " ", 1, at - 1):gmatch("[^+]+") do
        pad[name:match("^%s*(.-)%s*$")] = true
    end
    advance(tonumber(args[at]) or 30, pad)
    if args[at + 1] then
        joypad.set(pad, 1)
        client.screenshot(dir .. "\\" .. args[at + 1] .. ".png")
        log("shot " .. args[at + 1] .. ".png")
    end
    advance(2)
end

function commands.stick(args)
    advance(tonumber(args[3]) or 4, nil, { ["X Axis"] = tonumber(args[1]), ["Y Axis"] = tonumber(args[2]) })
    advance(2)
end

function commands.wait(args) advance(tonumber(args[1]) or 1) end

function commands.shot(args)
    emu.frameadvance()
    client.screenshot(dir .. "\\" .. args[1] .. ".png")
    log("shot " .. args[1] .. ".png")
end

function commands.save(args) savestate.save(dir .. "\\" .. args[1] .. ".State") log("saved " .. args[1]) end

function commands.load(args) savestate.load(dir .. "\\" .. args[1] .. ".State") log("loaded " .. args[1]) end

function commands.read(args)
    local base, len = to_offset(args[1]), tonumber(args[2])
    local bytes = memory.read_bytes_as_array(base, len, RDRAM)
    for row = 0, len - 1, 16 do
        local line = string.format("%08X:", 0x80000000 + base + row)
        for i = row + 1, math.min(row + 16, len) do line = line .. string.format(" %02X", bytes[i]) end
        log(line)
    end
end

function commands.dump(args)
    local bytes = memory.read_bytes_as_array(to_offset(args[1]), tonumber(args[2]), RDRAM)
    local f = assert(io.open(dir .. "\\" .. args[3] .. ".bin", "wb"))
    local chunk = {}
    for i = 1, #bytes do
        chunk[#chunk + 1] = string.char(bytes[i])
        if #chunk == 4096 then f:write(table.concat(chunk)) chunk = {} end
    end
    f:write(table.concat(chunk))
    f:close()
    log("dumped " .. #bytes .. " bytes to " .. args[3] .. ".bin")
end

function commands.find(args)
    local needle = hex_bytes(table.concat(args))
    local size = memory.getmemorydomainsize(RDRAM)
    local hits = 0
    local block = 0x10000
    for base = 0, size - 1, block do
        local len = math.min(block + #needle - 1, size - base)
        local bytes = memory.read_bytes_as_array(base, len, RDRAM)
        for i = 1, len - #needle + 1 do
            if bytes[i] == needle[1] then
                local match = true
                for j = 2, #needle do
                    if bytes[i + j - 1] ~= needle[j] then match = false break end
                end
                if match and i <= block then
                    hits = hits + 1
                    if hits <= 64 then log(string.format("%08X", 0x80000000 + base + i - 1)) end
                end
            end
        end
    end
    log(hits .. " match(es)")
end

function commands.u32(args)
    log(string.format("%08X", memory.read_u32_be(to_offset(args[1]), RDRAM)))
end

function commands.write(args)
    local base = to_offset(args[1])
    local bytes = hex_bytes(table.concat(args, "", 2))
    for i = 1, #bytes do memory.write_u8(base + i - 1, bytes[i], RDRAM) end
    log("wrote " .. #bytes .. " bytes")
end

function commands.turbo(args)
    local on = args[1] == "on"
    emu.limitframerate(not on)
    client.speedmode(on and 6400 or 100)
end

function commands.frame() log("frame " .. emu.framecount()) end

-- eval <lua>: run a chunk and print what it returns (tables are listed key=value).
function commands.eval(args)
    local chunk, err = (loadstring or load)(table.concat(args, " "))
    if not chunk then log("syntax error: " .. tostring(err)) return end
    for _, v in ipairs({ chunk() }) do
        if type(v) == "table" then
            local keys = {}
            for k in pairs(v) do keys[#keys + 1] = tostring(k) end
            table.sort(keys)
            for _, k in ipairs(keys) do log(k .. "=" .. tostring(v[k])) end
        else
            log(tostring(v))
        end
    end
end

function commands.exit() client.exit() end

local function run_file()
    local f = io.open(cmd_path, "r")
    if not f then return end
    local lines = {}
    for line in f:lines() do lines[#lines + 1] = line end
    f:close()
    os.remove(cmd_path)
    out = {}
    for _, line in ipairs(lines) do
        local words = {}
        for w in line:gmatch("%S+") do words[#words + 1] = w end
        local name = table.remove(words, 1)
        if name and name:sub(1, 1) ~= "#" then
            local fn = commands[name]
            if fn then
                local ok, err = pcall(fn, words)
                if not ok then log("error in '" .. line .. "': " .. tostring(err)) end
            else
                log("unknown command: " .. name)
            end
        end
    end
    local d = assert(io.open(done_path .. ".tmp", "w"))
    d:write(table.concat(out, "\n"), "\n")
    d:close()
    os.remove(done_path)
    os.rename(done_path .. ".tmp", done_path)
end

client.SetSoundOn(false)
console.log("stadium2 remote ready: " .. dir)
local ready = io.open(dir .. "\\ready.txt", "w")
if ready then ready:write(emu.getsystemid(), "\n") ready:close() end

while true do
    run_file()
    emu.frameadvance()
end

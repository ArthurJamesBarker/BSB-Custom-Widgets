# Debug Next Bus (telnet + log)

If the app stays on **Loading...** or you want to see why fetch fails:

## 1. Connect to the Busy Bar CLI

From your Mac (Busy Bar on same network, use its IP if not USB):

```bash
telnet 10.0.4.20
```

At the `>:` prompt, turn on debug logging:

```text
log debug
```

Leave this terminal open.

## 2. Launch the app on the device

On the Busy Bar: **APPS → next_bus**. Watch the **telnet** window. You should see:

- Any **Lua errors** (syntax, nil value, etc.)
- Any **fetch**-related messages or errors the firmware prints when `busy.fetch.get` is used

If the fetch fails or the callback never runs, the log may show why (e.g. connection refused, timeout, DNS).

## 3. Optional: test fetch from the CLI

At the `>:` prompt you can try the device’s **fetch** command to see if it can reach your proxy (syntax may vary):

```text
fetch http://10.46.21.104:8787/arrivals?stop=490000037S&limit=2
```

If this fails, the Bar can’t reach your Mac (firewall, wrong IP, or different Wi‑Fi). If it works, the problem is likely in the Lua app or its callback.

## 4. Other useful commands

- **`log`** — restore normal log level  
- **`top`** — show running tasks  
- **Start + Back** — hard reboot the device

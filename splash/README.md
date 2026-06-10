# 🎆 PATCH IS ON — full-screen splash

A self-contained, full-screen fireworks splash that announces a patch is live.
Fourth-of-July themed (red / white / blue), runs for **~3 minutes**, then ends
with a grand finale.

## Run it

```bash
./splash/launch.sh
```

This opens a kiosk/full-screen browser if one is available (Chromium, Chrome,
Firefox), otherwise falls back to your default browser — press **F** for
fullscreen, **Esc** to exit.

Or just open `splash/patch-is-on.html` directly in any browser.

## What it is

- Pure HTML/CSS/JS canvas animation — **no dependencies, no build, no install**.
- Self-contained single file (`patch-is-on.html`); nothing is written to disk.
- Show length is the `RUN_MS` constant (180000 ms) in `patch-is-on.html`.

> Not a boot splash — this is a GUI/browser full-screen splash you launch on demand.

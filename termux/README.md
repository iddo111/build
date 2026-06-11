# One-tap SSH to iddo1 (Termux home-screen icon)

This makes a home-screen **icon** on your Android phone that, when tapped,
opens Termux and connects straight to your PC **iddo1** (`100.73.8.105`).

It uses **Termux:Widget**, which turns any script in `~/.shortcuts/` into a
tappable home-screen shortcut.

## Setup (on your phone)

1. Install **Termux** and **Termux:Widget** (use the same source for both —
   F-Droid is recommended; don't mix F-Droid and Play Store builds).
2. Open Termux and get these files onto the phone. Easiest:
   ```bash
   pkg install -y git
   git clone <this-repo-url>
   cd build/termux
   bash install.sh
   ```
3. Long-press your home screen → **Widgets** → **Termux:Widget** → drop it on
   the home screen → pick **ssh-iddo1**.
4. Tap the icon. Done — it connects to iddo1.

## Passwordless login (recommended)

`install.sh` creates an SSH key and prints the public half. Add it to iddo1:
```bash
ssh-copy-id iddo1@100.73.8.105
```
After that, tapping the icon logs in with no password prompt.

## Notes

- Edit `USER`, `HOST`, or `PORT` at the top of `.shortcuts/ssh-iddo1.sh` if
  your username on the PC isn't `iddo1` or you use a non-standard port.
- `100.73.8.105` is a **Tailscale** IP, so your phone must be on the same
  tailnet (Tailscale app installed and logged in) for the icon to reach the PC.
- The script auto-reconnects if the link drops; type `exit` to close cleanly.

#!/data/data/com.termux/files/usr/bin/bash
#
# Tap-to-connect SSH shortcut for Termux:Widget.
# When this script lives in ~/.shortcuts/ it shows up as a home-screen icon.
# Tapping the icon opens a Termux session and connects straight to iddo1.

# --- Config -------------------------------------------------------------
HOST="100.73.8.105"   # iddo1 (Tailscale IP)
USER="iddo1"          # change if your username on the PC differs
PORT="22"
# ------------------------------------------------------------------------

echo "Connecting to ${USER}@${HOST} ..."

# Keep the connection alive and reconnect on drop so a single tap "just works".
while true; do
    ssh -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o StrictHostKeyChecking=accept-new \
        -p "${PORT}" \
        "${USER}@${HOST}"

    code=$?
    # Clean exit (you typed `exit` / logout) -> stop.
    if [ $code -eq 0 ]; then
        echo "Session closed."
        break
    fi

    echo
    echo "Disconnected (exit ${code}). Reconnecting in 3s... (Ctrl-C to stop)"
    sleep 3
done

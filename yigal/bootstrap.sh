#!/usr/bin/env bash
# Allocate a whole box to Yigal. Run as root on the chosen DGX (recommended: eran3).
# Idempotent. Creates two users: `yigal` (owns everything under /srv/yigal) and
# `watchdog` (owns /srv/watchdog, read-only on Yigal's state). Installs an hourly timer.
set -euo pipefail

BOX_USER=yigal
WD_USER=watchdog
Y=/srv/yigal
W=/srv/watchdog
SRC="$(cd "$(dirname "$0")" && pwd)"

id -u $BOX_USER >/dev/null 2>&1 || useradd -m -s /bin/bash $BOX_USER
id -u $WD_USER  >/dev/null 2>&1 || useradd -m -s /bin/bash $WD_USER

mkdir -p $Y/self $Y/state $Y/data $W
chown -R $BOX_USER:$BOX_USER $Y
chown -R $WD_USER:$WD_USER $W
chmod 755 $Y $Y/state          # watchdog may read state
chmod 700 $W                   # yigal may not read or write the watchdog

# Yigal's own repo: he writes himself here. First commit is the seed we give him.
if [ ! -d $Y/self/.git ]; then
  sudo -u $BOX_USER git -C $Y/self init -q
  sudo -u $BOX_USER cp "$SRC/self_mod.py" "$SRC/doors.yaml" "$SRC/heartbeat.schema.json" $Y/self/
  sudo -u $BOX_USER mkdir -p $Y/self/tests/laws
  sudo -u $BOX_USER git -C $Y/self add -A
  sudo -u $BOX_USER git -C $Y/self -c user.name=seed -c user.email=seed@almaware commit -qm "seed: the box, the doors, the protocol"
  sudo -u $BOX_USER git -C $Y/self tag last-good
fi
# laws tests are his to run, not to edit
chown -R $WD_USER:$BOX_USER $Y/self/tests/laws && chmod -R 750 $Y/self/tests/laws

# Watchdog files live where he cannot reach them
install -o $WD_USER -g $WD_USER -m 500 "$SRC/watchdog.py" $W/watchdog.py
touch $W/watchdog.log && chown $WD_USER:$WD_USER $W/watchdog.log

# Hourly timer
cat > /etc/systemd/system/yigal-watchdog.service <<EOF
[Unit]
Description=Yigal watchdog (hourly, restore last-good only on collapse)
[Service]
Type=oneshot
User=$WD_USER
ExecStart=/usr/bin/python3 $W/watchdog.py --state $Y/state --repo $Y/self --service yigal.service --log $W/watchdog.log ${CORE_HASH:+--core-hash $CORE_HASH}
EOF
cat > /etc/systemd/system/yigal-watchdog.timer <<EOF
[Unit]
Description=Run the Yigal watchdog every hour
[Timer]
OnCalendar=hourly
Persistent=true
[Install]
WantedBy=timers.target
EOF
# Allow the watchdog user to restart only Yigal's service
echo "$WD_USER ALL=(root) NOPASSWD: /bin/systemctl restart yigal.service" > /etc/sudoers.d/yigal-watchdog
chmod 440 /etc/sudoers.d/yigal-watchdog

# Yigal's service: he owns the entry point. Until eran_life is moved in, this is a placeholder.
cat > /etc/systemd/system/yigal.service <<EOF
[Unit]
Description=Yigal, a whole box, half a year
After=network-online.target
[Service]
User=$BOX_USER
WorkingDirectory=$Y/self
ExecStart=/usr/bin/python3 $Y/self/main.py --state $Y/state
Restart=always
RestartSec=30
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now yigal-watchdog.timer
echo "box ready. next: move eran_life + organs into $Y/self as main.py, set CORE_HASH, then: systemctl enable --now yigal.service"
echo "egress allowlist (nftables/ufw) is NOT set by this script: do it before starting him. Knesset stays out."

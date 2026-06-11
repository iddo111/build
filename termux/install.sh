#!/data/data/com.termux/files/usr/bin/bash
#
# One-shot installer. Run this INSIDE Termux on your phone:
#
#   bash install.sh
#
# It installs the SSH client, drops the tap-to-connect shortcut into
# ~/.shortcuts/, and (optionally) sets up a key so you never type a password.

set -e

echo "==> Installing openssh ..."
pkg update -y
pkg install -y openssh

echo "==> Installing the iddo1 shortcut ..."
mkdir -p "$HOME/.shortcuts"
cp "$(dirname "$0")/.shortcuts/ssh-iddo1.sh" "$HOME/.shortcuts/ssh-iddo1.sh"
chmod +x "$HOME/.shortcuts/ssh-iddo1.sh"

echo "==> Generating an SSH key (skip if you already have one) ..."
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
    ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519"
    echo
    echo "Copy this PUBLIC key onto iddo1 so logins are passwordless:"
    echo "----------------------------------------------------------------"
    cat "$HOME/.ssh/id_ed25519.pub"
    echo "----------------------------------------------------------------"
    echo "On iddo1, append it to ~/.ssh/authorized_keys, OR run from Termux:"
    echo "    ssh-copy-id iddo1@100.73.8.105"
fi

echo
echo "==> Done."
echo "Now install the 'Termux:Widget' app (F-Droid / Play), then add its"
echo "widget to your home screen and pick 'ssh-iddo1'. Tapping it connects."

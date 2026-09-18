#!/usr/bin/env python3
"""
Yigal watchdog. Runs once an hour (systemd timer or cron) as a DIFFERENT user
than Yigal, from a directory Yigal cannot write to.

It does exactly one thing: decides whether Yigal has collapsed on himself.
If not, it exits. If yes, it restores the `last-good` tag of Yigal's own
repository, restarts his service, and writes one line to the log.

It never edits his code, never tunes his parameters, never judges his choices.
Slow progress is not collapse. Weird architecture is not collapse. Silence on
Shabbat is not collapse.

Usage:
  watchdog.py --state /srv/yigal/state --repo /srv/yigal/self \
              --service yigal.service --log /srv/watchdog/watchdog.log \
              [--core-hash <sha256 of the frozen 192 dims>] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

THRESHOLDS = {
    "heartbeat_max_age_s": 2 * 3600,      # אין פעימת לב שעתיים
    "restarts_24h_max": 5,                # לולאת קריסה
    "stagnation_hours": 48,               # התקדמות אפס בכל הדלתות
    "entropy_min_bits": 1.0,              # התנוונות: אותו צליל שוב ושוב
    "entropy_hours": 24,
    "disk_free_min_frac": 0.10,           # חנק
    "mem_used_max_frac": 0.95,
    "mem_hours": 6,
}


def now() -> float:
    return time.time()


def log(path: Path, msg: str) -> None:
    line = f"{dt.datetime.now(dt.timezone.utc).isoformat()} {msg}"
    print(line)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def history_append(hist_path: Path, hb: dict, keep_hours: int = 72) -> list[dict]:
    """Keep a rolling window of heartbeats so multi-hour conditions can be judged."""
    hist = read_json(hist_path) or []
    hist.append({"t": hb.get("t", now()),
                 "progress_all_zero": all(v <= 0 for v in (hb.get("progress") or {}).values() or [0]),
                 "entropy": hb.get("mouth_entropy_bits"),
                 "mem": hb.get("mem_used_frac"),
                 "disk": hb.get("disk_free_frac")})
    cutoff = now() - keep_hours * 3600
    hist = [h for h in hist if h["t"] >= cutoff]
    hist_path.write_text(json.dumps(hist), encoding="utf-8")
    return hist


def sustained(hist: list[dict], key: str, pred, hours: int) -> bool:
    """True if pred(value) held for every sample in the last `hours` and there were samples."""
    cutoff = now() - hours * 3600
    window = [h for h in hist if h["t"] >= cutoff]
    if len(window) < max(2, hours // 2):      # need enough samples to judge
        return False
    return all(pred(h.get(key)) for h in window)


def is_shabbat(t: float | None = None) -> bool:
    """Coarse: Friday 17:30 to Saturday 20:30 Israel time. Good enough for 'do not panic'."""
    il = dt.timezone(dt.timedelta(hours=3))  # IDT; adjust in winter
    d = dt.datetime.fromtimestamp(t or now(), il)
    if d.weekday() == 4 and d.hour >= 17:
        return True
    if d.weekday() == 5 and d.hour < 21:
        return True
    return False


def collapse_reasons(hb: dict | None, hb_age: float, hist: list[dict], core_hash: str | None) -> list[str]:
    r = []
    if hb is None:
        return ["no heartbeat file"]
    if hb_age > THRESHOLDS["heartbeat_max_age_s"]:
        r.append(f"heartbeat stale {hb_age/3600:.1f}h")
    if hb.get("restarts_24h", 0) >= THRESHOLDS["restarts_24h_max"]:
        r.append(f"crash loop: {hb['restarts_24h']} restarts in 24h")
    if not is_shabbat() and sustained(hist, "progress_all_zero", lambda v: v is True, THRESHOLDS["stagnation_hours"]):
        r.append(f"stagnation: zero progress on every door for {THRESHOLDS['stagnation_hours']}h")
    if not is_shabbat() and sustained(hist, "entropy", lambda v: v is not None and v < THRESHOLDS["entropy_min_bits"], THRESHOLDS["entropy_hours"]):
        r.append("degeneracy: mouth entropy collapsed for 24h")
    if hb.get("disk_free_frac", 1.0) < THRESHOLDS["disk_free_min_frac"]:
        r.append(f"disk nearly full: {hb['disk_free_frac']:.2f} free")
    if sustained(hist, "mem", lambda v: v is not None and v > THRESHOLDS["mem_used_max_frac"], THRESHOLDS["mem_hours"]):
        r.append("memory pinned above 95% for 6h")
    if core_hash and hb.get("core_hash") and hb["core_hash"] != core_hash:
        r.append("frozen core hash changed (law of growth broken)")
    return r


def restore_last_good(repo: Path, service: str, dry: bool, logp: Path) -> None:
    cmds = [
        ["git", "-C", str(repo), "tag", "-f", f"collapse-{int(now())}", "HEAD"],  # keep the wreck, never delete
        ["git", "-C", str(repo), "checkout", "-f", "last-good"],
        ["sudo", "-n", "systemctl", "restart", service],
    ]
    for c in cmds:
        log(logp, ("DRY " if dry else "") + " ".join(c))
        if not dry:
            subprocess.run(c, check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", type=Path, required=True, help="dir with heartbeat.json (Yigal writes, we read)")
    ap.add_argument("--repo", type=Path, required=True, help="Yigal's own git repo")
    ap.add_argument("--service", default="yigal.service")
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--core-hash", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    hb_path = a.state / "heartbeat.json"
    hb = read_json(hb_path)
    hb_age = now() - hb_path.stat().st_mtime if hb_path.exists() else float("inf")
    hist = history_append(a.log.parent / "heartbeat_history.json", hb or {}, keep_hours=72)

    reasons = collapse_reasons(hb, hb_age, hist, a.core_hash)
    if not reasons:
        log(a.log, f"ok age={hb_age/60:.0f}m ver={(hb or {}).get('self_version','?')[:8]} note={(hb or {}).get('note','')[:80]!r}")
        return 0

    log(a.log, "COLLAPSE " + " | ".join(reasons))
    restore_last_good(a.repo, a.service, a.dry_run, a.log)
    return 2


if __name__ == "__main__":
    sys.exit(main())

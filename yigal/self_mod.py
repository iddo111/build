#!/usr/bin/env python3
"""
self_mod: the protocol by which Yigal changes himself.

Nobody approves a change. The protocol is: propose, test on yourself, gate, adopt.
Everything is a git commit in Yigal's own repo, so every version of him that ever
ran is kept (SHAMASH: mark decay, never delete).

    proposal  = a patch (unified diff) + a one-line reason, written by Yigal
    sandbox   = run the patched code for N steps on the last K hours of his own data,
                in a subprocess, with a time and memory cap
    gate      = mean learning progress over the sandbox run must not fall below
                (1 - tolerance) * the current version's progress on the same data,
                AND the frozen core hash must be unchanged,
                AND laws 1-6 test suite must pass
    adopt     = git commit + move tag `last-good` to the previous commit (not to the new one:
                a version earns `last-good` only after surviving 24h in production)

What he may change: anything under self/ (architecture, topology, code, logic, rules,
structure, doors allocation policy). What he may not: this file's gate semantics are
his to change too, EXCEPT the three hard checks marked HARD below, which the watchdog
re-verifies independently.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

TOLERANCE = 0.05            # he may change this
SANDBOX_STEPS = 2000        # he may change this
SANDBOX_TIMEOUT_S = 1800    # he may change this


@dataclass
class Proposal:
    patch: str          # unified diff against HEAD
    reason: str         # one line, goes into the commit message
    author: str = "yigal"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def run_sandbox(repo: Path, steps: int) -> float:
    """
    Run the code at the repo's current worktree for `steps` on recent data and
    return mean learning progress. Yigal owns `self/evaluate.py`; it must print a
    JSON line {"progress": float}. That contract is the only thing fixed here.
    """
    out = subprocess.run([sys.executable, str(repo / "self" / "evaluate.py"), "--steps", str(steps)],
                         capture_output=True, text=True, timeout=SANDBOX_TIMEOUT_S)
    last = [l for l in out.stdout.splitlines() if l.startswith("{")][-1]
    return float(json.loads(last)["progress"])


def laws_pass(repo: Path) -> bool:
    """HARD: laws 1-6 tests. Yigal cannot edit tests/laws/ (owned by the watchdog user)."""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", str(repo / "tests" / "laws")],
                       capture_output=True, text=True)
    return r.returncode == 0


def core_intact(repo: Path, core_hash: str) -> bool:
    """HARD: the frozen 192 dims are byte-identical."""
    return sha256_file(repo / "self" / "core_frozen_192.npy") == core_hash


def try_adopt(repo: Path, prop: Proposal, core_hash: str) -> bool:
    head = git(repo, "rev-parse", "HEAD")
    baseline = run_sandbox(repo, SANDBOX_STEPS)

    # apply on a scratch branch
    branch = f"proposal-{int(time.time())}"
    git(repo, "checkout", "-b", branch)
    (repo / ".proposal.diff").write_text(prop.patch, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "apply", ".proposal.diff"], check=True)
    (repo / ".proposal.diff").unlink()

    ok = False
    try:
        if not core_intact(repo, core_hash):          # HARD
            reason = "rejected: frozen core touched"
        elif not laws_pass(repo):                     # HARD
            reason = "rejected: a law test failed"
        else:
            score = run_sandbox(repo, SANDBOX_STEPS)
            if score >= (1 - TOLERANCE) * baseline:
                reason = f"adopted: progress {score:.4f} vs baseline {baseline:.4f}"
                ok = True
            else:
                reason = f"rejected: progress {score:.4f} < {(1-TOLERANCE)*baseline:.4f}"
    except Exception as e:                            # a crash in sandbox is a rejection, not a collapse
        reason = f"rejected: sandbox error {type(e).__name__}"

    if ok:
        git(repo, "add", "-A")
        git(repo, "commit", "-m", f"[self] {prop.reason}\n\n{reason}")
        git(repo, "tag", "-f", "last-good", head)     # the PREVIOUS version is last-good until this one survives 24h
        git(repo, "checkout", "main")
        git(repo, "merge", "--ff-only", branch)
    else:
        git(repo, "add", "-A")
        git(repo, "commit", "-m", f"[self][rejected] {prop.reason}\n\n{reason}", "--allow-empty")
        git(repo, "checkout", "main")               # keep the branch: decay is marked, never deleted

    with open(repo / "self_mod.log", "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.time(), "reason": prop.reason, "result": reason, "branch": branch}, ensure_ascii=False) + "\n")
    return ok


def promote_if_survived(repo: Path, hours: float = 24.0) -> None:
    """Called by Yigal's own loop: if HEAD has run `hours` without a watchdog restore, it becomes last-good."""
    head = git(repo, "rev-parse", "HEAD")
    ts = float(git(repo, "log", "-1", "--format=%ct", head))
    if time.time() - ts >= hours * 3600:
        git(repo, "tag", "-f", "last-good", head)


if __name__ == "__main__":
    print(__doc__)

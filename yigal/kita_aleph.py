#!/usr/bin/env python3
"""
KITA ALEPH - the first classroom of ERAN's self-learning university.

A board of Hebrew letter tiles (letter + niqqud). ERAN looks at the board with
his own eye, presses a tile with his own hand, and the world answers with a
HUMAN recording of that syllable. No label is ever given. The only signal is
the consequence: what he heard after what he pressed.

Iron laws honored:
  Law of Labels      - every clip filename names its human speaker.
  Synthetic Death    - no TTS anywhere. Clips come only from human mouths
                       (FLEURS-he / ivrit.ai segments, force-aligned).
  Law of the Judge   - this file never decides that anything "works".
                       It only logs. Iddo's ear decides.
  Law 6 (proposed)   - no label, only consequence.

Usage:
  python kita_aleph.py --clips ./human_syllables --fonts ./fonts --steps 2000 \
                       --log ./kita_aleph.jsonl

Clip directory layout (one dir per tile, files named <speaker>_<n>.wav):
  human_syllables/
    a/    fleurs_spk0142_1.wav  fleurs_spk0917_1.wav ...
    ba/   ...
    ga/   ...

Integration points for the organs are the three functions marked ORGAN PORT.
Until they are wired, the env runs with a random hand so the loop can be
smoke-tested end to end.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Tiles: (id, glyph). Start tiny: open vowels and the /ba/ family ERAN already
# found by himself. Add rows only when the board is "boring" (low surprise).
TILES_LEVEL_1 = [
    ("a",  "אַ"),   # ah
    ("ba", "בָּ"),  # ba
    ("ma", "מָ"),  # ma
    ("aba", "אַבָּא"),  # the Sukkot word. Never rendered as audio by us.
]
TILES_LEVEL_2 = TILES_LEVEL_1 + [
    ("ga", "גָ"), ("da", "דָ"), ("la", "לָ"), ("na", "נָ"), ("sha", "שָׁ"),
]


@dataclass
class Step:
    t: float
    step: int
    board: list[str]          # tile ids in the order shown (left to right)
    fonts: list[str]          # font file used per tile (eye sees unseen typefaces)
    pressed: int              # index the hand pressed
    heard_clip: str | None    # path of the human clip the world answered with
    heard_speaker: str | None
    surprise: float | None    # filled by the JEPA port, None if unwired


class KitaAleph:
    def __init__(self, clips_dir: Path, fonts_dir: Path, level: int = 1,
                 tile_px: int = 160, seed: int | None = None):
        self.rng = random.Random(seed)
        self.tiles = TILES_LEVEL_1 if level == 1 else TILES_LEVEL_2
        self.clips_dir = clips_dir
        self.fonts = sorted(p for p in fonts_dir.glob("*.[to]tf"))
        if not self.fonts:
            raise SystemExit(f"no .ttf/.otf fonts in {fonts_dir}")
        self.tile_px = tile_px
        self.clips = {tid: sorted((clips_dir / tid).glob("*.wav"))
                      for tid, _ in self.tiles}
        missing = [tid for tid, c in self.clips.items() if not c and tid != "aba"]
        if missing:
            raise SystemExit(f"no human clips for tiles: {missing}")
        self.step_n = 0

    # ---------------------------------------------------------------- board
    def render(self) -> tuple[Image.Image, list[str], list[str]]:
        order = self.tiles[:]
        self.rng.shuffle(order)
        n = len(order)
        img = Image.new("L", (self.tile_px * n, self.tile_px), 255)
        draw = ImageDraw.Draw(img)
        used_fonts = []
        for i, (tid, glyph) in enumerate(order):
            font_path = self.rng.choice(self.fonts)
            size = self.rng.randint(int(self.tile_px * 0.45), int(self.tile_px * 0.7))
            font = ImageFont.truetype(str(font_path), size)
            x0 = i * self.tile_px
            # small jitter so the eye never sees the same pixels twice
            jx = self.rng.randint(-8, 8)
            jy = self.rng.randint(-8, 8)
            bbox = draw.textbbox((0, 0), glyph, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((x0 + (self.tile_px - w) / 2 + jx, (self.tile_px - h) / 2 + jy),
                      glyph, font=font, fill=0)
            draw.rectangle([x0, 0, x0 + self.tile_px - 1, self.tile_px - 1], outline=128)
            used_fonts.append(font_path.name)
        return img, [tid for tid, _ in order], used_fonts

    # ------------------------------------------------------------ the world
    def answer(self, tid: str) -> Path | None:
        """The only feedback in the universe: a human voice saying the syllable."""
        if tid == "aba":
            # Milestone words are never hand-rendered. The board stays silent.
            return None
        return self.rng.choice(self.clips[tid])

    # ------------------------------------------------------------ one cycle
    def step(self, log) -> Step:
        img, order, fonts = self.render()
        eye_gist = ORGAN_eye(img)                 # ORGAN PORT
        pressed = ORGAN_hand(eye_gist, len(order))  # ORGAN PORT
        clip = self.answer(order[pressed])
        surprise = None
        speaker = None
        if clip is not None:
            speaker = clip.stem.split("_")[0]
            surprise = ORGAN_ear_and_jepa(eye_gist, pressed, clip)  # ORGAN PORT
        rec = Step(t=time.time(), step=self.step_n, board=order, fonts=fonts,
                   pressed=pressed, heard_clip=str(clip) if clip else None,
                   heard_speaker=speaker, surprise=surprise)
        log.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        log.flush()
        self.step_n += 1
        return rec


# ====================================================================== PORTS
# Replace these three with calls over the organ-port wire (ORGANS.lock).
# They are deliberately dumb so the loop can be run tonight without the fleet.

def ORGAN_eye(img: Image.Image):
    """Return the eye's gist vector for the board image."""
    return img  # placeholder: pass the raw image through


def ORGAN_hand(eye_gist, n_tiles: int) -> int:
    """Return the tile index the hand presses. Random until wired."""
    return random.randrange(n_tiles)


def ORGAN_ear_and_jepa(eye_gist, pressed: int, clip: Path) -> float:
    """
    Feed the clip to CARFAC, get the ear gist, and return JEPA's surprise:
    distance between the sound-gist predicted BEFORE pressing and the
    sound-gist actually heard. That number, and nothing else, moves him.
    """
    return float("nan")


# ======================================================================= main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", type=Path, required=True)
    ap.add_argument("--fonts", type=Path, required=True)
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--log", type=Path, default=Path("kita_aleph.jsonl"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--save-boards", type=Path, default=None,
                    help="optional dir to dump board PNGs for Iddo's eye")
    a = ap.parse_args()

    env = KitaAleph(a.clips, a.fonts, level=a.level, seed=a.seed)
    if a.save_boards:
        a.save_boards.mkdir(parents=True, exist_ok=True)
    with open(a.log, "a", encoding="utf-8") as log:
        for i in range(a.steps):
            rec = env.step(log)
            if a.save_boards and i % 50 == 0:
                img, _, _ = env.render()
                img.save(a.save_boards / f"board_{rec.step:06d}.png")
    print(f"{env.step_n} steps logged to {a.log}. No result until Iddo's ear says so.")


if __name__ == "__main__":
    main()

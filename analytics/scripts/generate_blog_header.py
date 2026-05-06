"""Generate the case-study blog header image, matching the existing
Envio case-study design (Sablier, Polymarket): black background, orange
ENVIO wordmark top-left, white headline, orange concentric ring
decoration on the right, simple circular badge."""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.patheffects import withStroke

OUT = Path(__file__).resolve().parent.parent / "output" / "privacy-pools-case-study.png"
OUT.parent.mkdir(exist_ok=True)

W, H = 1200, 672  # close to the existing 484x267 ratio at 2.5x
DPI = 200

ORANGE = "#FF5722"
ORANGE_SOFT = "#FF8A50"
BG = "#0b0b0b"
WHITE = "#FFFFFF"


def main() -> None:
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    aspect = W / H  # canvas-aspect-corrected coords so circles stay round
    ax.set_xlim(0, aspect)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.set_axis_off()

    # Concentric rings on the right (decorative)
    cx, cy = aspect - 0.30, 0.50
    for r, a in [(0.55, 0.04), (0.45, 0.07), (0.36, 0.11), (0.27, 0.16)]:
        circle = mpatches.Circle(
            (cx, cy), r,
            fill=False, edgecolor=ORANGE, alpha=a, linewidth=1.4,
        )
        ax.add_patch(circle)

    # Subtle hex grid behind the rings (texture)
    rng = np.random.default_rng(7)
    for _ in range(60):
        x = rng.uniform(aspect - 0.7, aspect + 0.05)
        y = rng.uniform(-0.05, 1.05)
        size = rng.uniform(0.012, 0.02)
        alpha = rng.uniform(0.04, 0.10)
        hex_patch = mpatches.RegularPolygon(
            (x, y), numVertices=6, radius=size,
            orientation=np.radians(30), fill=False,
            edgecolor=ORANGE, alpha=alpha, linewidth=0.8,
        )
        ax.add_patch(hex_patch)

    # ENVIO wordmark
    fig.text(
        0.05, 0.82, "ENVIO",
        fontsize=26, fontweight="bold", color=ORANGE,
        family="DejaVu Sans",
    )

    # Headline — short enough to clear the right-side badge.
    fig.text(
        0.05, 0.60, "Privacy",
        fontsize=58, fontweight="bold", color=WHITE,
        family="DejaVu Sans",
    )
    fig.text(
        0.05, 0.40, "in Public",
        fontsize=58, fontweight="bold", color=WHITE,
        family="DejaVu Sans",
    )

    # Subtitle pill
    fig.text(
        0.05, 0.20, "Case Study: Privacy Pools",
        fontsize=14, color=ORANGE, family="DejaVu Sans",
    )

    # Right-side badge: white circle with an orange lock glyph.
    badge_radius = 0.16
    badge = mpatches.Circle(
        (cx, cy), badge_radius,
        facecolor=WHITE, edgecolor=ORANGE, linewidth=2.5, zorder=5,
    )
    ax.add_patch(badge)

    # Lock body
    lock_w, lock_h = 0.130, 0.110
    lock_cx, lock_cy = cx, cy - 0.010
    lock_body = mpatches.FancyBboxPatch(
        (lock_cx - lock_w / 2, lock_cy - lock_h / 2),
        lock_w, lock_h,
        boxstyle="round,pad=0.0,rounding_size=0.020",
        facecolor=ORANGE, edgecolor=ORANGE, zorder=6,
    )
    ax.add_patch(lock_body)

    # Shackle: open arc above the body
    shackle_y = lock_cy + lock_h / 2 + 0.005
    shackle = mpatches.Arc(
        (lock_cx, shackle_y), 0.090, 0.100,
        angle=0, theta1=0, theta2=180,
        color=ORANGE, linewidth=7, zorder=7, capstyle="round",
    )
    ax.add_patch(shackle)

    # Keyhole
    kh = mpatches.Circle(
        (lock_cx, lock_cy + 0.012), 0.014,
        facecolor=WHITE, zorder=8,
    )
    ax.add_patch(kh)
    kh_stem = mpatches.Rectangle(
        (lock_cx - 0.005, lock_cy - 0.022), 0.010, 0.030,
        facecolor=WHITE, zorder=8,
    )
    ax.add_patch(kh_stem)

    fig.savefig(OUT, dpi=DPI, facecolor=BG, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f"wrote: {OUT}")


if __name__ == "__main__":
    main()

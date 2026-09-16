from __future__ import annotations

from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


BG = "#141820"
PANEL = "#202633"
TEXT = "#E8ECF2"
ACCENT = "#D35B43"
TEAL = "#58B7A8"


def bar_chart(labels: list[str], values: list[float], title: str, ylabel: str = "%") -> BytesIO:
    fig, ax = plt.subplots(figsize=(7.2, 3.0), facecolor=BG)
    ax.set_facecolor(PANEL)
    bars = ax.bar(labels, values, color=[ACCENT if value < 50 else TEAL for value in values])
    ax.set_title(title, color=TEXT, fontsize=12, pad=10)
    ax.set_ylabel(ylabel, color=TEXT)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.grid(axis="y", color="#414958", alpha=0.45)
    for spine in ax.spines.values():
        spine.set_color("#414958")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.1f}", ha="center", va="bottom", color=TEXT, fontsize=8)
    fig.tight_layout()
    stream = BytesIO()
    fig.savefig(stream, format="png", dpi=145, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    stream.seek(0)
    return stream


def available_bar(rows: list[dict[str, Any]], label_key: str, value_key: str, title: str, limit: int = 12) -> BytesIO | None:
    selected = [row for row in rows if row.get(value_key) is not None][:limit]
    if not selected:
        return None
    return bar_chart([str(row[label_key]) for row in selected], [float(row[value_key]) for row in selected], title)


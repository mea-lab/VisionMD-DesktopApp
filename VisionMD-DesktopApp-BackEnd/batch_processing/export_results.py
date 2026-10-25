"""Model-independent batch companions; export existing results, never re-infer.

CSV is long-form (feature,value) to support task-specific schemas. Values and
units in original feature names are preserved; quality is technical, not clinical.
"""
import csv
import math
from pathlib import Path

import numpy as np


def export_companions(result, output_json, *, fps, task, video, candidate=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    base = Path(output_json).with_suffix("")
    png = base.with_name(base.name + "_signal.png")
    csv_path = base.with_name(base.name + "_features.csv")
    quality = result["analysisQuality"]
    series = []
    line = result.get("linePlot", {})
    if isinstance(line, dict) and len(line.get("data", [])):
        series.append(("Analysis signal", line["data"], line.get("time")))
    signals = result.get("signals", {})
    if isinstance(signals, dict):
        series.extend((name, values, None) for name, values in signals.items())
    elif isinstance(signals, (list, tuple)):
        series.append(("Analysis signal", signals, None))
    numeric = []
    for name, values, times in series:
        try:
            values = np.asarray(values, dtype=float)
        except (ValueError, TypeError):
            continue
        if values.ndim != 1 or not values.size:
            continue
        # linePlot carries exact analysis timestamps. Gait/tremor signals are
        # frame-indexed at source fps; do not infer time from array length.
        time = np.asarray(times, dtype=float) if times is not None else np.arange(values.size) / fps
        if time.shape != values.shape:
            raise ValueError(f"Timestamp count mismatch for {name}")
        numeric.append((name, values, time))
    fig, axes = plt.subplots(max(1, len(numeric)), 1, figsize=(12, max(4, 2.4 * len(numeric))),
                             squeeze=False)
    try:
        for ax, (name, values, times) in zip(axes[:, 0], numeric):
            ax.plot(times, values, linewidth=1.2, color="#1f77b4", label="Trace")
            # Use the exact saved events displayed by VisionMD. Never detect
            # new peaks here or attach cycle events to unrelated gait signals.
            if name == "Analysis signal" and isinstance(line, dict) and len(line.get("data", [])):
                for key, label, marker_color in (
                    ("peaks", "Peak values", "#decd6d"),
                    ("valleys_start", "Valley start", "#76B041"),
                    ("valleys_end", "Valley end", "red"),
                ):
                    event = result.get(key) or {}
                    x = np.asarray(event.get("time", []), dtype=float)
                    y = np.asarray(event.get("data", []), dtype=float)
                    if x.ndim != 1 or y.ndim != 1 or x.size != y.size:
                        raise ValueError(f"Invalid saved event coordinates: {key}")
                    valid = np.isfinite(x) & np.isfinite(y)
                    ax.scatter(x[valid], y[valid], s=40, color=marker_color,
                               label=label, zorder=3)
            ax.legend(loc="upper right", bbox_to_anchor=(1, .86), framealpha=.9)
            ax.set_ylabel(name)
            ax.set_xlabel("Time [s]")
            ax.grid(color="#d1d5db", linewidth=.7)
            ax.axhline(0, color="#888888", linewidth=.7, zorder=0)
            ax.spines[["top", "right"]].set_visible(False)
        if not numeric:
            axes[0, 0].text(.5, .5, "No usable signal", ha="center", transform=axes[0, 0].transAxes)
        color = {"good": "#19733b", "review": "#8a5700", "failed": "#b82020"}.get(quality["status"], "#555555")
        # An overlay remains visible when the plot is viewed without its JSON.
        axes[0, 0].text(.99, .98, f"Estimated quality: {quality['label']}",
                        transform=axes[0, 0].transAxes, ha="right", va="top",
                        color="white", bbox={"facecolor": color, "alpha": .9, "pad": 6})
        title = f"{video} | {task}" + (f" | {candidate}" if candidate else "")
        fig.suptitle(title)
        fig.text(.01, .01, "Automated technical quality only; not clinical validation.", fontsize=9)
        fig.tight_layout(rect=(0, .04, 1, .96))
        fig.savefig(png, dpi=150)
    finally:
        plt.close(fig)
    rows = [("video", str(video)), ("task", task),
            ("estimated_quality", quality["label"]),
            ("quality_reasons", "; ".join(quality.get("reasons", [])))]
    if candidate:
        rows.insert(2, ("candidate", candidate))
    def scalars(mapping, prefix=""):
        for key, value in mapping.items():
            name = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                yield from scalars(value, name)
            elif value is None or isinstance(value, (str, bool, int, float, np.number)):
                if isinstance(value, (float, np.floating)) and not math.isfinite(value):
                    value = "NA"
                yield name, value
    radar = result.get("radarTable", {})
    if isinstance(radar, dict):
        rows.extend(scalars(radar, "radarTable"))
    # Gait and tremor publish their estimated features as top-level scalars.
    rows.extend((key, value) for key, value in scalars(
        {key: value for key, value in result.items() if not isinstance(value, (dict, list, tuple, np.ndarray))}
    ))
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["feature", "value"])
        writer.writerows(rows)
    return {"signal_png": str(png), "features_csv": str(csv_path)}

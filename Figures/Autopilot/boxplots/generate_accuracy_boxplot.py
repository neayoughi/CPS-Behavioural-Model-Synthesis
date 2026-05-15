from __future__ import annotations

# Adapted copy of the paper-format plotting script used for the Autopilot accuracy boxplot.
# Kept under Figures as requested; reads the cleaned Autopilot RQ1 results by default.

import argparse
import os
from pathlib import Path

_CACHE_ROOT = Path(__file__).resolve().parent / ".plot-cache"
_MPL_CACHE = _CACHE_ROOT / "matplotlib"
_XDG_CACHE = _CACHE_ROOT / "xdg"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
_XDG_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(_XDG_CACHE))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon

try:
    from scipy.stats import binomtest
except ImportError:  # pragma: no cover
    from scipy.stats import binom_test as _legacy_binom_test

    def binomtest(k: int, n: int, p: float = 0.5, alternative: str = "two-sided"):
        class _Result:
            def __init__(self, pvalue: float):
                self.pvalue = pvalue

        return _Result(float(_legacy_binom_test(k, n=n, p=p, alternative=alternative)))


VARIABLES = ("pitchwheel", "throttle", "pitchwheel_throttle")
METHODS = ("mela", "manual")
METHOD_LABELS = {"mela": "MELA", "manual": "MANUAL"}
COLORS = {"mela": "#1f77b4", "manual": "#ff7f0e"}
MODE_LABELS = {"pitchwheel": "Pitchwheel", "throttle": "Throttle", "pitchwheel_throttle": "Pitchwheel + throttle"}
MEANPROPS = {"linestyle": "dashed", "linewidth": 5, "color": "black"}



def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Results").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate project root from {start}")

PROJECT_ROOT = find_project_root(Path(__file__))
ANALYSIS_DIR = Path(__file__).resolve().parent
DEFAULT_RUN_DIR = PROJECT_ROOT / "Results" / "RQ1" / "Autopilot" / "accuracy" / "descend" / "method_comparison"
RUN_DIR = DEFAULT_RUN_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the Autopilot accuracy boxplot.")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=DEFAULT_RUN_DIR,
        help="Evaluation run folder containing accuracy_reports. Defaults to the cleaned descend RQ1 result folder.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ANALYSIS_DIR,
        help="Folder for generated figure outputs. Defaults to this Figures/Autopilot/boxplots folder.",
    )
    return parser.parse_args()

plt.rcParams.update(
    {
        "font.size": 24,
        "font.weight": "bold",
        "axes.labelweight": "bold",
        "axes.titleweight": "bold",
        "xtick.labelsize": 20,
        "ytick.labelsize": 20,
    }
)


def normalize_method(value: str) -> str | None:
    token = str(value).strip().lower()
    if token == "mela":
        return "mela"
    if token == "manual":
        return "manual"
    return None


def normalize_mode(value: str) -> str | None:
    token = str(value).strip().lower().replace("-", "_")
    aliases = {
        "pwheel": "pitchwheel",
        "pitchwheel": "pitchwheel",
        "throttle": "throttle",
        "both": "pitchwheel_throttle",
        "top_2": "pitchwheel_throttle",
        "pitchwheel_throttle": "pitchwheel_throttle",
    }
    return aliases.get(token)


def locate_accuracy_files(run_dir: Path) -> tuple[Path, Path]:
    preferred_dir = run_dir / "accuracy_reports"
    preferred_per_file = preferred_dir / "gsm_accuracy_per_file.csv"
    preferred_aggregate = preferred_dir / "gsm_accuracy_aggregate.csv"

    if preferred_per_file.exists() and preferred_aggregate.exists():
        return preferred_per_file, preferred_aggregate

    per_file_candidates = sorted(path for path in run_dir.rglob("accuracy_by_file.csv") if ANALYSIS_DIR not in path.parents)
    aggregate_candidates = sorted(path for path in run_dir.rglob("accuracy_summary.csv") if ANALYSIS_DIR not in path.parents)

    if not per_file_candidates or not aggregate_candidates:
        raise FileNotFoundError(f"Could not find required GSM accuracy CSV files under {run_dir}")

    return per_file_candidates[0], aggregate_candidates[0]


def load_accuracy_tables(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    per_file_path, aggregate_path = locate_accuracy_files(run_dir)
    per_file = pd.read_csv(per_file_path)
    aggregate = pd.read_csv(aggregate_path)

    required_per_file = {
        "method",
        "selected_row_count",
        "partial_accuracy_pct",
        "full_success",
        "correct_rows",
        "total_rows",
    }
    required_aggregate = {
        "method",
        "full_successes",
        "total_sequences",
        "full_accuracy_pct",
        "correct_rows",
        "total_rows",
        "partial_accuracy_pct",
    }

    missing_per_file = sorted(required_per_file - set(per_file.columns))
    missing_aggregate = sorted(required_aggregate - set(aggregate.columns))
    if missing_per_file:
        raise ValueError(f"Missing required per-file columns: {missing_per_file}")
    if missing_aggregate:
        raise ValueError(f"Missing required aggregate columns: {missing_aggregate}")

    per_file = per_file.copy()
    aggregate = aggregate.copy()

    # If mode column is missing, extract it from model_file
    if "mode" not in per_file.columns:
        def extract_mode(model_file: str) -> str:
            if "pwheel" in model_file and "throttle" in model_file:
                return "pitchwheel_throttle"
            elif "pwheel" in model_file:
                return "pitchwheel"
            elif "throttle" in model_file:
                return "throttle"
            else:
                return "unknown"
        per_file["mode"] = per_file["model_file"].map(extract_mode)

    if "mode" not in aggregate.columns:
        aggregate["mode"] = aggregate["model_file"].map(extract_mode)

    per_file["method"] = per_file["method"].map(normalize_method)
    per_file["mode"] = per_file["mode"].map(normalize_mode)
    aggregate["method"] = aggregate["method"].map(normalize_method)
    aggregate["mode"] = aggregate["mode"].map(normalize_mode)
    per_file = per_file.dropna(subset=["method", "mode"])
    aggregate = aggregate.dropna(subset=["method", "mode"])

    if "segment_id" not in per_file.columns:
        per_file["segment_id"] = per_file.groupby(["method", "mode"]).cumcount() + 1

    numeric_columns = [
        "segment_id",
        "selected_row_count",
        "partial_accuracy_pct",
        "full_success",
        "correct_rows",
        "total_rows",
    ]
    for column in numeric_columns:
        per_file[column] = pd.to_numeric(per_file[column], errors="coerce")

    aggregate_numeric = [
        "full_successes",
        "total_sequences",
        "full_accuracy_pct",
        "correct_rows",
        "total_rows",
        "partial_accuracy_pct",
    ]
    for column in aggregate_numeric:
        aggregate[column] = pd.to_numeric(aggregate[column], errors="coerce")

    return per_file, aggregate, per_file_path, aggregate_path


def build_paired_table(per_file: pd.DataFrame) -> pd.DataFrame:
    key_columns = [
        "mode",
        "segment_id",
        "selected_row_count",
    ]
    value_columns = ["partial_accuracy_pct", "full_success", "correct_rows", "total_rows"]

    mela = (
        per_file[per_file["method"] == "mela"][key_columns + value_columns]
        .rename(columns={column: f"mela_{column}" for column in value_columns})
        .copy()
    )
    manual = (
        per_file[per_file["method"] == "manual"][key_columns + value_columns]
        .rename(columns={column: f"manual_{column}" for column in value_columns})
        .copy()
    )

    paired = pd.merge(mela, manual, on=key_columns, how="inner", validate="one_to_one")
    paired["partial_accuracy_diff_pct_points"] = paired["mela_partial_accuracy_pct"] - paired["manual_partial_accuracy_pct"]
    paired["full_success_diff"] = paired["mela_full_success"] - paired["manual_full_success"]
    paired = paired.sort_values(["mode", "segment_id"]).reset_index(drop=True)
    return paired


def a12(mela_values: list[float], manual_values: list[float]) -> float | None:
    if not mela_values or not manual_values:
        return None

    more = 0.0
    same = 0.0
    for mela_value in mela_values:
        for manual_value in manual_values:
            if mela_value > manual_value:
                more += 1.0
            elif mela_value == manual_value:
                same += 1.0

    return (more + 0.5 * same) / (len(mela_values) * len(manual_values))


def effect_direction(a12_value: float | None) -> str:
    if a12_value is None:
        return ""
    if a12_value > 0.5:
        return "MELA > MANUAL"
    if a12_value < 0.5:
        return "MANUAL > MELA"
    return "tie"


def effect_size_label(a12_value: float | None) -> str:
    if a12_value is None or np.isnan(a12_value):
        return "NA"
    if a12_value >= 0.71 or a12_value <= 0.29:
        return "Large"
    if (0.64 <= a12_value <= 0.71) or (0.29 <= a12_value <= 0.36):
        return "Medium"
    if (0.56 < a12_value < 0.64) or (0.36 < a12_value < 0.44):
        return "Small"
    return "Negligible"


def mann_whitney_pvalue(mela_values: list[float], manual_values: list[float]) -> float | None:
    if not mela_values or not manual_values:
        return None
    try:
        result = mannwhitneyu(mela_values, manual_values, alternative="two-sided", method="auto")
        return float(result.pvalue)
    except TypeError:  # pragma: no cover
        result = mannwhitneyu(mela_values, manual_values, alternative="two-sided")
        return float(result.pvalue)


def wilcoxon_pvalue(mela_values: list[float], manual_values: list[float]) -> float | None:
    if not mela_values or not manual_values or len(mela_values) != len(manual_values):
        return None

    differences = np.asarray(mela_values, dtype=float) - np.asarray(manual_values, dtype=float)
    nonzero = differences[np.abs(differences) > 1e-12]
    if nonzero.size == 0:
        return None

    try:
        result = wilcoxon(mela_values, manual_values, alternative="two-sided", zero_method="wilcox", method="auto")
        return float(result.pvalue)
    except TypeError:  # pragma: no cover
        result = wilcoxon(mela_values, manual_values, alternative="two-sided", zero_method="wilcox")
        return float(result.pvalue)
    except ValueError:
        return None


def sign_test_pvalue(differences: list[float]) -> float | None:
    non_ties = [difference for difference in differences if abs(float(difference)) > 1e-12]
    if not non_ties:
        return None
    positive = sum(1 for difference in non_ties if difference > 0)
    return float(binomtest(positive, len(non_ties), p=0.5, alternative="two-sided").pvalue)


def exact_mcnemar_pvalue(mela_binary: list[int], manual_binary: list[int]) -> tuple[float | None, int, int]:
    if len(mela_binary) != len(manual_binary):
        return None, 0, 0

    mela_only = sum(1 for mela_value, manual_value in zip(mela_binary, manual_binary) if mela_value == 1 and manual_value == 0)
    manual_only = sum(1 for mela_value, manual_value in zip(mela_binary, manual_binary) if mela_value == 0 and manual_value == 1)
    discordant = mela_only + manual_only
    if discordant == 0:
        return None, mela_only, manual_only
    pvalue = float(binomtest(mela_only, discordant, p=0.5, alternative="two-sided").pvalue)
    return pvalue, mela_only, manual_only


def compute_statistics(paired: pd.DataFrame, aggregate: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for mode in VARIABLES:
        paired_mode = paired[paired["mode"] == mode].copy()
        if paired_mode.empty:
            continue

        mela_partial = paired_mode["mela_partial_accuracy_pct"].astype(float).tolist()
        manual_partial = paired_mode["manual_partial_accuracy_pct"].astype(float).tolist()
        differences = (paired_mode["mela_partial_accuracy_pct"] - paired_mode["manual_partial_accuracy_pct"]).astype(float).tolist()
        mela_full = paired_mode["mela_full_success"].astype(int).tolist()
        manual_full = paired_mode["manual_full_success"].astype(int).tolist()

        aggregate_mela = aggregate[(aggregate["mode"] == mode) & (aggregate["method"] == "mela")].iloc[0]
        aggregate_manual = aggregate[(aggregate["mode"] == mode) & (aggregate["method"] == "manual")].iloc[0]

        a12_value = a12(mela_partial, manual_partial)
        mcnemar_pvalue, mela_only, manual_only = exact_mcnemar_pvalue(mela_full, manual_full)

        rows.append(
            {
                "mode": mode,
                "n_pairs": int(len(paired_mode)),
                "aggregate_partial_accuracy_pct_mela": float(aggregate_mela["partial_accuracy_pct"]),
                "aggregate_partial_accuracy_pct_manual": float(aggregate_manual["partial_accuracy_pct"]),
                "aggregate_full_accuracy_pct_mela": float(aggregate_mela["full_accuracy_pct"]),
                "aggregate_full_accuracy_pct_manual": float(aggregate_manual["full_accuracy_pct"]),
                "mean_partial_accuracy_pct_mela": float(np.mean(mela_partial)),
                "mean_partial_accuracy_pct_manual": float(np.mean(manual_partial)),
                "median_partial_accuracy_pct_mela": float(np.median(mela_partial)),
                "median_partial_accuracy_pct_manual": float(np.median(manual_partial)),
                "std_partial_accuracy_pct_mela": float(np.std(mela_partial, ddof=1)) if len(mela_partial) > 1 else 0.0,
                "std_partial_accuracy_pct_manual": float(np.std(manual_partial, ddof=1)) if len(manual_partial) > 1 else 0.0,
                "mean_difference_pct_points": float(np.mean(differences)),
                "median_difference_pct_points": float(np.median(differences)),
                "mela_higher_pairs": int(sum(1 for difference in differences if difference > 1e-12)),
                "manual_higher_pairs": int(sum(1 for difference in differences if difference < -1e-12)),
                "tied_pairs": int(sum(1 for difference in differences if abs(difference) <= 1e-12)),
                "mann_whitney_u_pvalue": mann_whitney_pvalue(mela_partial, manual_partial),
                "wilcoxon_signed_rank_pvalue": wilcoxon_pvalue(mela_partial, manual_partial),
                "sign_test_pvalue": sign_test_pvalue(differences),
                "exact_mcnemar_full_success_pvalue": mcnemar_pvalue,
                "mela_only_full_success_discordant_pairs": mela_only,
                "manual_only_full_success_discordant_pairs": manual_only,
                "A12_mela_vs_manual": a12_value,
                "effect_direction": effect_direction(a12_value),
                "effect_size_label": effect_size_label(a12_value),
            }
        )

    return pd.DataFrame(rows)


def save_paired_table(paired: pd.DataFrame) -> Path:
    output_path = ANALYSIS_DIR / "paired_partial_accuracy_by_file.csv"
    paired.to_csv(output_path, index=False)
    return output_path


def style_axis_frame(ax) -> None:
    for label in ax.get_xticklabels():
        label.set_weight("bold")
    for label in ax.get_yticklabels():
        label.set_weight("bold")
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)


def expand_weighted_percentages(values: list[float], weights: list[float]) -> list[float]:
    expanded: list[float] = []
    for value, weight in zip(values, weights):
        count = int(round(float(weight)))
        if count <= 0:
            continue
        expanded.extend([float(value)] * count)
    return expanded


def plot_paired_boxplots(ax, mela_values: list[float], manual_values: list[float], title: str) -> None:
    data = [mela_values, manual_values]
    box = ax.boxplot(data, meanprops=MEANPROPS, meanline=True, showmeans=True, widths=0.55)

    linewidth = 2
    plt.setp(box["boxes"], linewidth=linewidth, color="black")
    plt.setp(box["whiskers"], linewidth=linewidth, color="black")
    plt.setp(box["caps"], linewidth=linewidth, color="black")
    plt.setp(box["medians"], linewidth=3, color="orange")
    for median_line in box["medians"]:
        median_line.set_zorder(6)

    means = [float(item.get_ydata()[0]) for item in box["means"]]
    for index, mean_value in enumerate(means, start=1):
        ax.text(
            index,
            mean_value,
            f"{mean_value:.2f}",
            ha="center",
            va="bottom",
            fontsize=18,
            color="black",
            weight="bold",
            bbox={"facecolor": "gray", "alpha": 0.4, "edgecolor": "none", "boxstyle": "round,pad=0.5"},
        )

    ax.set_xticks([1, 2])
    ax.set_xticklabels(["\n".join(["MELA"]), "\n".join(["MANUAL"])], fontdict={"fontvariant": "small-caps"})
    ax.set_title(title, fontdict={"fontname": "monospace"}, pad=20)
    ax.set_ylabel("Accuracy(%)")
    ax.set_ylim(bottom=0, top=110)
    ax.grid(axis="y", linestyle="--", alpha=0.25)

    for mean_line in box["means"]:
        mean_line.set_color("blue")
        mean_line.set_linewidth(5)
        mean_line.set_linestyle("solid")
        mean_line.set_zorder(5)

    style_axis_frame(ax)


def save_boxplots(paired: pd.DataFrame) -> tuple[Path, Path]:
    fig, axes = plt.subplots(1, 3, figsize=(18, 7), constrained_layout=True)

    for axis, mode in zip(axes, VARIABLES):
        paired_mode = paired[paired["mode"] == mode].copy()
        weights = paired_mode["selected_row_count"].astype(float).tolist()
        mela_values = expand_weighted_percentages(
            paired_mode["mela_partial_accuracy_pct"].astype(float).tolist(),
            weights,
        )
        manual_values = expand_weighted_percentages(
            paired_mode["manual_partial_accuracy_pct"].astype(float).tolist(),
            weights,
        )
        plot_paired_boxplots(
            axis,
            mela_values,
            manual_values,
            MODE_LABELS[mode],
        )

    pdf_path = ANALYSIS_DIR / "accuracy_boxplot.pdf"
    png_path = ANALYSIS_DIR / "accuracy_boxplot.png"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return pdf_path, png_path


def save_statistics(stats_df: pd.DataFrame) -> Path:
    output_path = ANALYSIS_DIR / "statistical_tests.csv"
    stats_df.to_csv(output_path, index=False)
    return output_path


def format_optional(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "NA"
    return f"{float(value):.6f}"


def main() -> None:
    global ANALYSIS_DIR, RUN_DIR
    args = parse_args()
    RUN_DIR = args.run_dir.resolve()
    ANALYSIS_DIR = (args.output_dir or (RUN_DIR / "analysis_outputs")).resolve()
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    per_file, aggregate, per_file_path, aggregate_path = load_accuracy_tables(RUN_DIR)
    paired = build_paired_table(per_file)
    stats_df = compute_statistics(paired, aggregate)

    paired_path = save_paired_table(paired)
    stats_path = save_statistics(stats_df)
    box_pdf, box_png = save_boxplots(paired)

    print(f"Analyzed workflow folder: {RUN_DIR}")
    print(f"Used per-file CSV: {per_file_path}")
    print(f"Used aggregate CSV: {aggregate_path}")
    print(f"Saved: {paired_path}")
    print(f"Saved: {stats_path}")
    print(f"Saved: {box_pdf}")
    print(f"Saved: {box_png}")


if __name__ == "__main__":
    main()

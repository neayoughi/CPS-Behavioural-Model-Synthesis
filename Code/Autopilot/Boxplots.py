from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


learning_sets = ["ascend", "descend"]
methods = ["MELA", "Baseline"]
configurations = ["pitchwheel", "throttle", "pitchwheel_throttle"]


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Results").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate project root from {start}")


project_root = find_project_root(Path(__file__))


def project_path(relative_path: str) -> Path:
    return project_root / relative_path


def read_accuracy_rows() -> pd.DataFrame:
    rows = []
    for learning_set in learning_sets:
        for method in methods:
            for configuration in configurations:
                accuracy_file_path = (
                    f"Results/RQ1/Autopilot/accuracy/"
                    f"{learning_set}/{method}/{configuration}_accuracy.csv"
                )
                path = project_path(accuracy_file_path)
                if not path.exists():
                    continue
                df = pd.read_csv(path)
                df["learning_set"] = learning_set
                df["method"] = method
                df["configuration"] = configuration
                rows.append(df)

    if not rows:
        raise SystemExit("No accuracy CSV files found.")
    return pd.concat(rows, ignore_index=True)


def save_boxplots() -> None:
    df = read_accuracy_rows()
    output_file_path = "Figures/Autopilot/boxplots/accuracy_boxplot.pdf"
    output_path = project_path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, len(configurations), figsize=(15, 5), constrained_layout=True)
    for axis, configuration in zip(axes, configurations):
        values = [
            df[(df["method"] == method) & (df["configuration"] == configuration)]["accuracy"].astype(float).tolist()
            for method in methods
        ]
        axis.boxplot(values, labels=methods, showmeans=True)
        axis.set_title(configuration)
        axis.set_ylabel("Accuracy (%)")
        axis.set_ylim(0, 110)
        axis.grid(axis="y", linestyle="--", alpha=0.25)

    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {output_file_path}")


if __name__ == "__main__":
    save_boxplots()

from __future__ import annotations

from pathlib import Path

import pandas as pd


learning_sets = ["ascend", "descend"]
configurations = ["pitchwheel", "throttle", "pitchwheel_throttle"]

mela_splits = {
    "ascend": {
        "pitchwheel": {"Pwheel_Level": ("Pwheel", 5.006334, 9.039527)},
        "throttle": {"Throttle_Level": ("Throttle", 0.498360, 0.944576)},
        "pitchwheel_throttle": {
            "Pwheel_Level": ("Pwheel", 5.006334, 10.728691),
            "Throttle_Level": ("Throttle", 0.402556, 0.495788),
        },
    },
    "descend": {
        "pitchwheel": {"Pwheel_Level": ("Pwheel", 4.137257, 19.958631)},
        "throttle": {"Throttle_Level": ("Throttle", 0.481133, 0.806384)},
        "pitchwheel_throttle": {
            "Pwheel_Level": ("Pwheel", 4.137257, 20.046238),
            "Throttle_Level": ("Throttle", 0.497785, 0.804406),
        },
    },
}


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Data").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate project root from {start}")


project_root = find_project_root(Path(__file__))


def project_path(relative_path: str) -> Path:
    return project_root / relative_path


def to_level(series: pd.Series, split_1: float, split_2: float) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    levels = pd.Series("", index=series.index, dtype=object)
    levels.loc[values <= split_1] = "low"
    levels.loc[(values > split_1) & (values <= split_2)] = "med"
    levels.loc[values > split_2] = "high"
    return levels


def write_mela_abstraction(learning_set: str, configuration: str) -> None:
    input_file_path = f"Data/Autopilot/Learning set/MELA/{learning_set}/{configuration}.csv"
    output_file_path = f"Data/Autopilot/Abstraction/MELA/{learning_set}/{configuration}.csv"

    input_path = project_path(input_file_path)
    output_path = project_path(output_file_path)

    if not input_path.exists():
        print(f"Skipping missing MELA learning set: {input_file_path}")
        return

    df = pd.read_csv(input_path)
    for level_column, (source_column, split_1, split_2) in mela_splits[learning_set][configuration].items():
        df[level_column] = to_level(df[source_column], split_1, split_2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Wrote {output_file_path}")


def main() -> None:
    for learning_set in learning_sets:
        for configuration in configurations:
            write_mela_abstraction(learning_set, configuration)


if __name__ == "__main__":
    main()

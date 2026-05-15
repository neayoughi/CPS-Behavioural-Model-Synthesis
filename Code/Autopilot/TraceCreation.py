from __future__ import annotations

from pathlib import Path

import pandas as pd


learning_sets = ["ascend", "descend"]
methods = ["MELA", "Baseline"]
configurations = ["pitchwheel", "throttle", "pitchwheel_throttle"]


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Data").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate project root from {start}")


project_root = find_project_root(Path(__file__))


def project_path(relative_path: str) -> Path:
    return project_root / relative_path


def input_token(row: dict, configuration: str) -> str:
    if configuration == "pitchwheel":
        return f"p:{str(row['Pwheel_Level']).lower()}"
    if configuration == "throttle":
        return f"t:{str(row['Throttle_Level']).lower()}"
    return f"p:{str(row['Pwheel_Level']).lower()} t:{str(row['Throttle_Level']).lower()}"


def create_trace(method: str, learning_set: str, configuration: str) -> None:
    abstraction_file_path = (
        f"Data/Autopilot/Abstraction/{method}/{learning_set}/{configuration}.csv"
    )
    trace_csv_path = f"Data/Autopilot/Trace/{method}/{learning_set}/{configuration}.csv"
    trace_file_path = f"Data/Autopilot/Trace/{method}/{learning_set}/{configuration}.txt"

    source_path = project_path(abstraction_file_path)
    output_csv_path = project_path(trace_csv_path)
    output_txt_path = project_path(trace_file_path)

    if not source_path.exists():
        print(f"Skipping missing abstraction file: {abstraction_file_path}")
        return

    df = pd.read_csv(source_path)
    tokens: list[str] = []
    trace_rows: list[dict[str, str]] = []
    trace_literal: list[tuple[list[str], str]] = []

    for row in df.to_dict(orient="records"):
        token = input_token(row, configuration)
        tokens.append(token)
        state = str(row["State"])
        trace_rows.append({"input": ",".join(tokens), "State": state})
        trace_literal.append((tokens.copy(), state))

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(trace_rows, columns=["input", "State"]).to_csv(output_csv_path, index=False)
    output_txt_path.write_text(repr(trace_literal), encoding="utf-8")
    print(f"Wrote {trace_csv_path}")
    print(f"Wrote {trace_file_path}")


def main() -> None:
    for method in methods:
        for learning_set in learning_sets:
            for configuration in configurations:
                create_trace(method, learning_set, configuration)


if __name__ == "__main__":
    main()

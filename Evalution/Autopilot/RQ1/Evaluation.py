from __future__ import annotations

from pathlib import Path

import pandas as pd
from aalpy.utils import load_automaton_from_file


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


def parse_input_trace(input_value: object) -> list[str]:
    return [token.strip() for token in str(input_value).split(",") if token.strip()]


def current_model_path(method: str, learning_set: str, configuration: str) -> Path | None:
    dot_path = (
        f"Results/LearnedModel/Autopilot/{method}/{learning_set}/gsm_models/{configuration}_model.dot"
    )
    path = project_path(dot_path)
    if path.exists():
        return path
    return None


def predict_state(automaton, input_tokens: list[str]) -> str | None:
    state = automaton.initial_state
    for token in input_tokens:
        if token not in state.transitions:
            return None
        state = state.transitions[token]
    return str(state.output)


def evaluate_trace(method: str, learning_set: str, configuration: str) -> None:
    trace_file_path = f"Evaluation/Autopilot/Trace/{method}/{learning_set}/{configuration}.csv"
    accuracy_file_path = (
        f"Results/RQ1/Autopilot/accuracy/{learning_set}/{method}/{configuration}_accuracy.csv"
    )

    trace_path = project_path(trace_file_path)
    model_path = current_model_path(method, learning_set, configuration)
    output_path = project_path(accuracy_file_path)

    if not trace_path.exists():
        print(f"Skipping missing test trace: {trace_file_path}")
        return
    if model_path is None:
        print(f"Skipping missing model for {method}/{learning_set}/{configuration}")
        return

    automaton = load_automaton_from_file(str(model_path), automaton_type="moore")
    df = pd.read_csv(trace_path)

    correct_steps = 0
    total_steps = len(df)
    for row in df.to_dict(orient="records"):
        predicted_state = predict_state(automaton, parse_input_trace(row["input"]))
        if predicted_state == str(row["State"]):
            correct_steps += 1

    accuracy = 100.0 * correct_steps / max(total_steps, 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "method": method,
                "configuration": configuration,
                "accuracy": round(accuracy, 2),
            }
        ]
    ).to_csv(output_path, index=False)
    print(f"Wrote {accuracy_file_path}")


def main() -> None:
    for learning_set in learning_sets:
        for method in methods:
            for configuration in configurations:
                evaluate_trace(method, learning_set, configuration)


if __name__ == "__main__":
    main()

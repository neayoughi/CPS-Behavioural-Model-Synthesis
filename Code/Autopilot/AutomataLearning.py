from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pandas as pd
from aalpy.learning_algs.general_passive.GeneralizedStateMerging import (
    GeneralizedStateMerging,
)


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


def load_traces(trace_csv_path: Path) -> list[tuple[list[str], str]]:
    df = pd.read_csv(trace_csv_path)
    traces = []
    for row in df.to_dict(orient="records"):
        traces.append((parse_input_trace(row["input"]), str(row["State"])))
    return traces


def count_transitions(automaton) -> int:
    return sum(len(state.transitions) for state in automaton.states)


def render_pdf(output_dot_path: Path) -> bool:
    dot = shutil.which("dot")
    if not dot:
        return False

    output_pdf_path = output_dot_path.with_suffix(".pdf")
    result = subprocess.run(
        [dot, "-Tpdf", str(output_dot_path), "-o", str(output_pdf_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and output_pdf_path.exists()


def learn_model(method: str, learning_set: str, configuration: str) -> None:
    trace_file_path = f"Data/Autopilot/Trace/{method}/{learning_set}/{configuration}.txt"
    trace_csv_path = f"Data/Autopilot/Trace/{method}/{learning_set}/{configuration}.csv"
    output_dot_path = (
        f"Results/LearnedModel/Autopilot/{method}/{learning_set}/{configuration}_model.dot"
    )
    model_summary_path = (
        f"Results/LearnedModel/Autopilot/{method}/{learning_set}/{configuration}_model_summary.txt"
    )

    trace_csv = project_path(trace_csv_path)
    output_dot = project_path(output_dot_path)
    summary_path = project_path(model_summary_path)

    if not trace_csv.exists():
        print(f"Skipping missing trace: {trace_csv_path}")
        return

    traces = load_traces(trace_csv)
    output_dot.parent.mkdir(parents=True, exist_ok=True)

    gsm = GeneralizedStateMerging(
        output_behavior="moore",
        transition_behavior="deterministic",
    )
    learned_model = gsm.run(traces)
    learned_model.save(file_path=output_dot.with_suffix(""), file_type="dot")
    pdf_written = render_pdf(output_dot)

    lines = [
        f"method: {method}",
        f"learning_set: {learning_set}",
        f"configuration: {configuration}",
        f"trace_file_path: {trace_file_path}",
        f"trace_csv_path: {trace_csv_path}",
        f"output_dot_path: {output_dot_path}",
        f"number_of_states: {len(learned_model.states)}",
        f"number_of_transitions: {count_transitions(learned_model)}",
        f"input_alphabet: {sorted(learned_model.get_input_alphabet())}",
        f"is_input_complete: {learned_model.is_input_complete()}",
        f"pdf_written: {pdf_written}",
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {output_dot_path}")


def main() -> None:
    for method in methods:
        for learning_set in learning_sets:
            for configuration in configurations:
                learn_model(method, learning_set, configuration)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from smv_model_checking_core import (
    CASE_DEFS,
    DOT_CONFIGS,
    SMV_ROOT,
    build_checker_model_text,
    build_rules,
    classify_ef,
    extract_declared_input_labels,
    find_nusmv,
    parse_spec_results,
    run_nusmv,
    write_csv,
)


MODEL_ROOT = SMV_ROOT
RESULTS_ROOT = SMV_ROOT


def model_path_for_config(config: dict[str, object]) -> Path:
    return MODEL_ROOT.joinpath(*config["model_subdir"]) / str(config["model_name"])


def output_case_for_config(config: dict[str, object]) -> str:
    return str(config["case_key"])


def target_dir_for_config(config: dict[str, object]) -> Path:
    return RESULTS_ROOT / str(config["family"]) / "check_results" / "property_checks" / output_case_for_config(config)


def checker_ef_path(target_dir: Path, case_key: str) -> Path:
    return target_dir / f"checker_{case_key}_ef.smv"


def checker_main_path(target_dir: Path, case_key: str) -> Path:
    return target_dir / f"checker_{case_key}_main.smv"


def output_ef_path(target_dir: Path, case_key: str) -> Path:
    return target_dir / f"output_{case_key}_ef.txt"


def output_main_path(target_dir: Path, case_key: str) -> Path:
    return target_dir / f"output_{case_key}_main.txt"


def summary_path(target_dir: Path, case_key: str) -> Path:
    return target_dir / f"summary_{case_key}.csv"


def report_path(target_dir: Path, case_key: str) -> Path:
    return target_dir / f"report_{case_key}.md"


def build_main_checker_text(model_text: str, rules, declared_labels: set[str]) -> tuple[str, list[str]]:
    spec_order: list[str] = []
    lines = [model_text.rstrip(), "", "-- Added main AG/AX gate specs", ""]
    for rule in rules:
        lines.append(f"-- {rule.rule_id} main")
        lines.append(rule.main_spec)
        spec_order.append(f"{rule.rule_id}::main")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", spec_order


def build_ef_checker_text(model_text: str, rules) -> tuple[str, list[str]]:
    spec_order: list[str] = []
    lines = [model_text.rstrip(), "", "-- Added gated EF checker specs", ""]
    for rule in rules:
        lines.append(f"-- {rule.rule_id} ef")
        lines.append(rule.ef_spec)
        spec_order.append(f"{rule.rule_id}::ef")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", spec_order


def write_report(path: Path, *, family: str, case_key: str, model_path: Path, rows: list[dict[str, str]]) -> None:
    ef_counts = {
        label: sum(1 for row in rows if row["final_status_EF"] == label)
        for label in ("REAL_FALSE", "VACUOUS_TRUE_EF", "REAL_TRUE")
    }
    main_counts = {
        label: sum(1 for row in rows if row["main_AG_AX_result"] == label)
        for label in ("FALSE", "TRUE")
    }

    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(row["final_status_EF"], []).append(row["rule_id"])

    lines = [
        f"# Final No-Sink AG/EF Report: {family} / {case_key}",
        "",
        f"- Model path: `{model_path}`",
        f"- Case type: `{CASE_DEFS[case_key]['case_type']}`",
        "",
        "## Status Counts",
        "",
        f"- Main FALSE: {main_counts['FALSE']}",
        f"- Main TRUE: {main_counts['TRUE']}",
        f"- EF REAL_FALSE: {ef_counts['REAL_FALSE']}",
        f"- EF VACUOUS_TRUE_EF: {ef_counts['VACUOUS_TRUE_EF']}",
        f"- EF REAL_TRUE: {ef_counts['REAL_TRUE']}",
        "",
        "## Classification Groups",
        "",
    ]
    for label in ("REAL_FALSE", "VACUOUS_TRUE_EF", "REAL_TRUE"):
        lines.append(f"### {label}")
        for rule_id in groups.get(label, []):
            lines.append(f"- `{rule_id}`")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    nusmv_path = find_nusmv()
    all_count = 0

    for config in DOT_CONFIGS:
        case_key = str(config["case_key"])
        family = str(config["family"])
        model_path = model_path_for_config(config)
        target_dir = target_dir_for_config(config)
        output_case = output_case_for_config(config)
        target_dir.mkdir(parents=True, exist_ok=True)

        model_text = model_path.read_text(encoding="utf-8")
        declared_labels = extract_declared_input_labels(model_text)
        expected_labels = list(CASE_DEFS[case_key]["input_labels"])
        if declared_labels != expected_labels:
            raise RuntimeError(
                f"No-sink model alphabet mismatch for {model_path}: "
                f"expected {expected_labels}, found {declared_labels}"
            )

        checker_model_text = build_checker_model_text(model_text, declared_labels)
        rules = build_rules(case_key)
        declared_label_set = set(declared_labels)
        undeclared = [rule.rule_id for rule in rules if rule.input_label not in declared_label_set]
        if undeclared:
            raise RuntimeError(f"No-sink checker found undeclared rule labels in {model_path}: {undeclared}")

        main_text, main_order = build_main_checker_text(checker_model_text, rules, declared_label_set)
        main_checker_file = checker_main_path(target_dir, output_case)
        ef_checker_file = checker_ef_path(target_dir, output_case)
        main_checker_file.write_text(main_text, encoding="utf-8")

        main_output = run_nusmv(nusmv_path, main_checker_file)
        output_main_path(target_dir, output_case).write_text(main_output, encoding="utf-8")
        main_results = parse_spec_results(main_output)
        if len(main_results) != len(main_order):
            raise RuntimeError(
                f"Parsed {len(main_results)} main results for {main_checker_file}, expected {len(main_order)}"
            )
        main_map = dict(zip(main_order, main_results))

        gated_rules = [rule for rule in rules if main_map[f"{rule.rule_id}::main"] == "TRUE"]
        ef_text, ef_order = build_ef_checker_text(checker_model_text, gated_rules)
        ef_checker_file.write_text(ef_text, encoding="utf-8")

        if ef_order:
            ef_output = run_nusmv(nusmv_path, ef_checker_file)
            ef_results = parse_spec_results(ef_output)
            if len(ef_results) != len(ef_order):
                raise RuntimeError(
                    f"Parsed {len(ef_results)} EF results for {ef_checker_file}, expected {len(ef_order)}"
                )
        else:
            ef_output = "-- No EF specs generated because no rule passed the main AG/AX gate.\n"
            ef_results = []
        output_ef_path(target_dir, output_case).write_text(ef_output, encoding="utf-8")
        ef_map = dict(zip(ef_order, ef_results))

        rows: list[dict[str, str]] = []
        for rule in rules:
            main_result = main_map[f"{rule.rule_id}::main"]
            ef_result = ef_map[f"{rule.rule_id}::ef"] if main_result == "TRUE" else "SKIPPED"
            rows.append(
                {
                    "rule_id": rule.rule_id,
                    "case_type": rule.case_type,
                    "transition_family": rule.transition_family,
                    "input_label": rule.input_label,
                    "antecedent": rule.antecedent,
                    "consequent": rule.consequent,
                    "declared_in_model": "TRUE",
                    "main_rule_generated_for_nusmv": "TRUE",
                    "main_AG_AX_result": main_result,
                    "EF_result": ef_result,
                    "final_status_EF": classify_ef(True, main_result, ef_result),
                }
            )

        fields = [
            "rule_id",
            "case_type",
            "transition_family",
            "input_label",
            "antecedent",
            "consequent",
            "declared_in_model",
            "main_rule_generated_for_nusmv",
            "main_AG_AX_result",
            "EF_result",
            "final_status_EF",
        ]
        write_csv(summary_path(target_dir, output_case), fields, rows)
        write_report(report_path(target_dir, output_case), family=family, case_key=case_key, model_path=model_path, rows=rows)

        all_count += 1
        print(f"Wrote {summary_path(target_dir, output_case)}")

    print(f"Completed AG/EF checking: {all_count} runs")


if __name__ == "__main__":
    main()

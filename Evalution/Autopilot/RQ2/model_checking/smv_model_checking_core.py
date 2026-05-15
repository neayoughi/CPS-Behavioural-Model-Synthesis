#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Results").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate Autopilot project root from {start}")

PROJECT_ROOT = find_project_root(Path(__file__))
ROOT = PROJECT_ROOT
SMV_ROOT = PROJECT_ROOT / "Results" / "RQ2" / "Autopilot"
LEARNED_MODEL_ROOT = PROJECT_ROOT / "Results" / "LearnedModel" / "Autopilot"

KNOWN_NUSMV_PATHS = [
    Path(os.environ["NUSMV_BIN"]) if os.environ.get("NUSMV_BIN") else None,
    shutil.which("NuSMV"),
    shutil.which("nusmv"),
]
KNOWN_NUSMV_PATHS = [Path(path) for path in KNOWN_NUSMV_PATHS if path]

CASE_DEFS = {
    "pitchwheel_throttle": {
        "case_type": "combined_input",
        "input_labels": [
            "p_low_t_low",
            "p_low_t_med",
            "p_low_t_high",
            "p_med_t_low",
            "p_med_t_med",
            "p_med_t_high",
            "p_high_t_low",
            "p_high_t_med",
            "p_high_t_high",
        ],
    },
    "pitchwheel": {
        "case_type": "p_only",
        "input_labels": ["p_low", "p_med", "p_high"],
    },
    "throttle": {
        "case_type": "t_only",
        "input_labels": ["t_low", "t_med", "t_high"],
    },
}

TRANSITION_FAMILIES = [
    ("critical_to_caution", "out_critical", "out_caution"),
    ("caution_to_nominal", "out_caution", "out_nominal"),
    ("nominal_to_caution", "out_nominal", "out_caution"),
    ("caution_to_critical", "out_caution", "out_critical"),
]

DOT_CONFIGS = [
    {
        "family": "ascend",
        "case_key": "pitchwheel_throttle",
        "dot_path": LEARNED_MODEL_ROOT
        / "MELA"
        / "ascend"
        / "gsm_models"
        / "pitchwheel_throttle_model.dot",
        "model_subdir": ("ascend", "generated_models", "pitchwheel_throttle"),
        "model_name": "pitchwheel_throttle_model.smv",
        "with_sink_name": "pitchwheel_throttle_model_with_sink.smv",
    },
    {
        "family": "ascend",
        "case_key": "pitchwheel",
        "dot_path": LEARNED_MODEL_ROOT
        / "MELA"
        / "ascend"
        / "gsm_models"
        / "pitchwheel_model.dot",
        "model_subdir": ("ascend", "generated_models", "pitchwheel"),
        "model_name": "pitchwheel_model.smv",
        "with_sink_name": "pitchwheel_model_with_sink.smv",
    },
    {
        "family": "ascend",
        "case_key": "throttle",
        "dot_path": LEARNED_MODEL_ROOT
        / "MELA"
        / "ascend"
        / "gsm_models"
        / "throttle_model.dot",
        "model_subdir": ("ascend", "generated_models", "throttle"),
        "model_name": "throttle_model.smv",
        "with_sink_name": "throttle_model_with_sink.smv",
    },
    {
        "family": "descend",
        "case_key": "pitchwheel_throttle",
        "dot_path": LEARNED_MODEL_ROOT
        / "MELA"
        / "descend"
        / "gsm_models"
        / "pitchwheel_throttle_model.dot",
        "model_subdir": ("descend", "generated_models", "pitchwheel_throttle"),
        "model_name": "pitchwheel_throttle_model.smv",
        "with_sink_name": "pitchwheel_throttle_model_with_sink.smv",
    },
    {
        "family": "descend",
        "case_key": "pitchwheel",
        "dot_path": LEARNED_MODEL_ROOT
        / "MELA"
        / "descend"
        / "gsm_models"
        / "pitchwheel_model.dot",
        "model_subdir": ("descend", "generated_models", "pitchwheel"),
        "model_name": "pitchwheel_model.smv",
        "with_sink_name": "pitchwheel_model_with_sink.smv",
    },
    {
        "family": "descend",
        "case_key": "throttle",
        "dot_path": LEARNED_MODEL_ROOT
        / "MELA"
        / "descend"
        / "gsm_models"
        / "throttle_model.dot",
        "model_subdir": ("descend", "generated_models", "throttle"),
        "model_name": "throttle_model.smv",
        "with_sink_name": "throttle_model_with_sink.smv",
    },
]

NODE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[(.*)\]\s*;?\s*$")
EDGE_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[(.*)\])?\s*;?\s*$"
)
ATTR_RE = re.compile(r'(\w+)\s*=\s*("((?:[^"\\]|\\.)*)"|[^,\]]+)')
INPUT_LABEL_RE = re.compile(r"input_label\s*:\s*\{([^}]*)\};", re.MULTILINE)
IVAR_BLOCK_RE = re.compile(
    r"IVAR\s+input_label\s*:\s*\{([^}]*)\};\s+VAR",
    re.MULTILINE,
)
INIT_STATE_RE = re.compile(r"(\binit\(state\)\s*:=\s*[^;]+;)")
SPEC_RESULT_RE = re.compile(r"^-- specification .* is (true|false)$", re.IGNORECASE)
SPEC_LINE_RE = re.compile(r"^-- specification (.*) is (true|false)$", re.IGNORECASE)
STATE_HEADER_RE = re.compile(r"^\s*-> State:\s*[^<]+<-\s*$")
ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")
OUTPUT_ALIAS_RE = re.compile(r"^\s*(out_[A-Za-z0-9_]+)\s*:=\s*([^;]+);", re.MULTILINE)

RESERVED = {
    "array",
    "assign",
    "boolean",
    "case",
    "constant",
    "constants",
    "define",
    "esac",
    "fairness",
    "frozenvar",
    "init",
    "invar",
    "ivar",
    "ltlspec",
    "module",
    "next",
    "self",
    "spec",
    "trans",
    "true",
    "false",
    "var",
}

SINK_STATE_KEY = "__sink__"
SINK_OUTPUT_LABEL = "SINK"


@dataclass(frozen=True)
class StateDef:
    dot_id: str
    output: str


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    label: str


@dataclass(frozen=True)
class ParsedMachine:
    source_path: Path
    states: OrderedDict[str, StateDef]
    transitions: list[Transition]
    initial_state: str


@dataclass(frozen=True)
class Rule:
    rule_id: str
    case_type: str
    transition_family: str
    input_label: str
    antecedent: str
    consequent: str
    source_output: str
    target_output: str
    main_spec: str
    ef_spec: str
    ltl_spec: str


def find_nusmv() -> str:
    for name in ("NuSMV", "nusmv"):
        path = shutil.which(name)
        if path:
            return path
    for path in KNOWN_NUSMV_PATHS:
        if path.exists():
            return str(path)
    raise SystemExit("Could not find a NuSMV binary.")


def parse_attributes(attr_text: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for match in ATTR_RE.finditer(attr_text or ""):
        key = match.group(1)
        whole_value = match.group(2)
        quoted_value = match.group(3)
        raw_value = quoted_value if whole_value.startswith('"') else whole_value
        attributes[key] = raw_value.strip().replace(r"\"", '"')
    return attributes


def split_state_output(raw_label: str, default_state: str) -> tuple[str, str]:
    label = raw_label.strip()
    if label.startswith("{") and label.endswith("}"):
        label = label[1:-1].strip()
    left, sep, right = label.partition("|")
    if sep and right.strip():
        return (left.strip() or default_state), right.strip()
    return default_state, label


def parse_dot(dot_path: Path) -> ParsedMachine:
    states: OrderedDict[str, StateDef] = OrderedDict()
    transitions: list[Transition] = []
    initial_state: str | None = None

    for raw_line in dot_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line in {"{", "}"} or line.startswith("digraph "):
            continue

        edge_match = EDGE_RE.match(line)
        if edge_match:
            source, target, attr_text = edge_match.groups()
            attrs = parse_attributes(attr_text or "")
            if source.startswith("__start"):
                if initial_state is not None and initial_state != target:
                    raise ValueError(
                        f"Multiple initial states detected in {dot_path}: {initial_state} and {target}"
                    )
                initial_state = target
                continue

            label = attrs.get("label", "").strip()
            if not label:
                raise ValueError(f"Missing edge label in {dot_path}: {line}")
            transitions.append(Transition(source=source, target=target, label=label))
            continue

        node_match = NODE_RE.match(line)
        if node_match:
            dot_id, attr_text = node_match.groups()
            if dot_id.startswith("__start"):
                continue
            attrs = parse_attributes(attr_text)
            raw_label = attrs.get("label")
            if raw_label is None:
                continue
            label_state, output = split_state_output(raw_label, dot_id)
            if label_state != dot_id:
                raise ValueError(
                    f"State label/name mismatch in {dot_path}: node={dot_id}, label={raw_label}"
                )
            states[dot_id] = StateDef(dot_id=dot_id, output=output)

    if not states:
        raise ValueError(f"No states found in {dot_path}")
    if initial_state is None:
        raise ValueError(f"No __start edge found in {dot_path}")

    for transition in transitions:
        if transition.source not in states:
            raise ValueError(f"Transition source {transition.source} is not declared in {dot_path}")
        if transition.target not in states:
            raise ValueError(f"Transition target {transition.target} is not declared in {dot_path}")

    return ParsedMachine(dot_path, states, transitions, initial_state)


def sanitize_identifier(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", text.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "value"
    if cleaned[0].isdigit():
        cleaned = f"id_{cleaned}"
    if cleaned in RESERVED:
        cleaned = f"{cleaned}_value"
    return cleaned


def build_unique_name_map(values: list[str]) -> dict[str, str]:
    used: set[str] = set()
    mapping: dict[str, str] = {}
    for value in values:
        base = sanitize_identifier(value)
        candidate = base
        index = 2
        while candidate in used:
            candidate = f"{base}_{index}"
            index += 1
        used.add(candidate)
        mapping[value] = candidate
    return mapping


def build_prefixed_name_map(values: list[str], prefix: str) -> dict[str, str]:
    used: set[str] = set()
    mapping: dict[str, str] = {}
    for value in values:
        base = f"{prefix}_{sanitize_identifier(value)}"
        candidate = base
        index = 2
        while candidate in used:
            candidate = f"{base}_{index}"
            index += 1
        used.add(candidate)
        mapping[value] = candidate
    return mapping


def symbolize_dot_labels(machine: ParsedMachine) -> tuple[list[str], dict[str, str], OrderedDict[tuple[str, str], str]]:
    raw_labels = list(OrderedDict((transition.label, None) for transition in machine.transitions).keys())
    label_name_map = build_unique_name_map(raw_labels)
    deterministic: OrderedDict[tuple[str, str], str] = OrderedDict()
    for transition in machine.transitions:
        label_symbol = label_name_map[transition.label]
        key = (transition.source, label_symbol)
        previous_target = deterministic.get(key)
        if previous_target is not None and previous_target != transition.target:
            raise ValueError(
                f"Non-deterministic transition for {transition.source} and {label_symbol}: "
                f"{previous_target} vs {transition.target}"
            )
        deterministic[key] = transition.target
    return raw_labels, label_name_map, deterministic


def validate_expected_alphabet(
    *,
    machine: ParsedMachine,
    case_key: str,
    dot_symbols: list[str],
) -> tuple[list[str], list[str], dict[str, str]]:
    expected_labels = list(CASE_DEFS[case_key]["input_labels"])
    unexpected = [symbol for symbol in dot_symbols if symbol not in expected_labels]
    if unexpected:
        raise ValueError(
            f"DOT model {machine.source_path} has labels outside expected {case_key} alphabet: "
            f"{', '.join(unexpected)}"
        )
    missing_expected = [label for label in expected_labels if label not in dot_symbols]
    return expected_labels, missing_expected, {label: label for label in dot_symbols}


def build_model(machine: ParsedMachine, case_key: str) -> str:
    dot_state_ids = list(machine.states.keys())
    state_names = build_unique_name_map(dot_state_ids)
    output_values = list(OrderedDict((state.output, None) for state in machine.states.values()).keys())
    output_names = build_prefixed_name_map(output_values, "out")
    raw_labels, label_name_map, deterministic = symbolize_dot_labels(machine)
    dot_symbols = [label_name_map[label] for label in raw_labels]
    expected_labels, missing_expected, _ = validate_expected_alphabet(
        machine=machine,
        case_key=case_key,
        dot_symbols=dot_symbols,
    )

    state_count = len(dot_state_ids)
    input_count = len(expected_labels)
    missing_count = state_count * input_count - len(deterministic)

    lines = [
        f"-- Source DOT: {machine.source_path}",
        f"-- Initial state: {machine.initial_state}",
        f"-- Regular states: {state_count}",
        f"-- Regular transitions: {len(machine.transitions)}",
        f"-- Full expected alphabet for case '{case_key}': {input_count}",
        f"-- DOT labels missing but still declared in alphabet: {', '.join(missing_expected) if missing_expected else 'none'}",
        f"-- Missing state/input pairs disallowed: {missing_count}",
        "-- Output mapping:",
    ]
    for output in output_values:
        lines.append(f'--   {output_names[output]} = "{output}"')
    lines.append("-- Input label mapping:")
    symbol_to_raw = {label_name_map[raw]: raw for raw in raw_labels}
    for label in expected_labels:
        origin = f'"{symbol_to_raw[label]}" from DOT' if label in symbol_to_raw else "added expected label"
        lines.append(f"--   {label} = {origin}")

    lines.extend(
        [
            "",
            "MODULE main",
            "",
            "IVAR",
            "  input_label : {" + ", ".join(expected_labels) + "};",
            "",
            "VAR",
            "  state : {" + ", ".join(state_names[state_id] for state_id in dot_state_ids) + "};",
            "",
            "DEFINE",
        ]
    )
    for index, output in enumerate(output_values):
        lines.append(f"  {output_names[output]} := {index};")
    first_output = output_names[output_values[0]]
    lines.extend(["", "  output := case"])
    for state_id in dot_state_ids:
        lines.append(
            f"    state = {state_names[state_id]} : {output_names[machine.states[state_id].output]};"
        )
    lines.append(f"    TRUE : {first_output};")
    lines.extend(
        [
            "  esac;",
            "",
            "ASSIGN",
            f"  init(state) := {state_names[machine.initial_state]};",
            "",
            "TRANS",
            "  case",
        ]
    )
    for (source, label_symbol), target in deterministic.items():
        lines.append(
            f"    state = {state_names[source]} & input_label = {label_symbol} : "
            f"next(state) = {state_names[target]};"
        )
    lines.extend(["    TRUE : FALSE;", "  esac;", ""])
    return "\n".join(lines)


def build_with_sink_model(machine: ParsedMachine, case_key: str) -> str:
    dot_state_ids = list(machine.states.keys())
    state_keys = dot_state_ids + [SINK_STATE_KEY]
    state_names = build_unique_name_map(state_keys)

    output_values = list(OrderedDict((state.output, None) for state in machine.states.values()).keys())
    all_outputs = output_values + [SINK_OUTPUT_LABEL]
    output_names = build_prefixed_name_map(all_outputs, "out")

    raw_labels, label_name_map, deterministic = symbolize_dot_labels(machine)
    dot_symbols = [label_name_map[label] for label in raw_labels]
    expected_labels, missing_expected, _ = validate_expected_alphabet(
        machine=machine,
        case_key=case_key,
        dot_symbols=dot_symbols,
    )

    state_count = len(dot_state_ids)
    input_count = len(expected_labels)
    missing_count = state_count * input_count - len(deterministic)

    lines = [
        f"-- Source DOT: {machine.source_path}",
        f"-- Initial state: {machine.initial_state}",
        f"-- Regular states: {state_count}",
        f"-- Regular transitions: {len(machine.transitions)}",
        f"-- Full expected alphabet for case '{case_key}': {input_count}",
        f"-- DOT labels missing but declared and routed to sink if used: {', '.join(missing_expected) if missing_expected else 'none'}",
        f"-- Missing state/input pairs routed to {state_names[SINK_STATE_KEY]}: {missing_count}",
        "-- Output mapping:",
    ]
    for output in output_values:
        lines.append(f'--   {output_names[output]} = "{output}"')
    lines.append(f'--   {output_names[SINK_OUTPUT_LABEL]} = "{SINK_OUTPUT_LABEL}"')
    lines.append("-- Input label mapping:")
    symbol_to_raw = {label_name_map[raw]: raw for raw in raw_labels}
    for label in expected_labels:
        origin = f'"{symbol_to_raw[label]}" from DOT' if label in symbol_to_raw else "added expected label"
        lines.append(f"--   {label} = {origin}")

    lines.extend(
        [
            "",
            "MODULE main",
            "",
            "IVAR",
            "  input_label : {" + ", ".join(expected_labels) + "};",
            "",
            "VAR",
            "  state : {" + ", ".join(state_names[key] for key in state_keys) + "};",
            "",
            "DEFINE",
        ]
    )
    for index, output in enumerate(all_outputs):
        lines.append(f"  {output_names[output]} := {index};")
    lines.extend(["", "  output := case"])
    for state_id in dot_state_ids:
        lines.append(
            f"    state = {state_names[state_id]} : {output_names[machine.states[state_id].output]};"
        )
    lines.append(f"    state = {state_names[SINK_STATE_KEY]} : {output_names[SINK_OUTPUT_LABEL]};")
    lines.append(f"    TRUE : {output_names[SINK_OUTPUT_LABEL]};")
    lines.extend(
        [
            "  esac;",
            "",
            "ASSIGN",
            f"  init(state) := {state_names[machine.initial_state]};",
            "",
            "  next(state) := case",
        ]
    )
    for (source, label_symbol), target in deterministic.items():
        lines.append(
            f"    state = {state_names[source]} & input_label = {label_symbol} : "
            f"{state_names[target]};"
        )
    lines.extend(
        [
            f"    state = {state_names[SINK_STATE_KEY]} : {state_names[SINK_STATE_KEY]};",
            f"    TRUE : {state_names[SINK_STATE_KEY]};",
            "  esac;",
            "",
        ]
    )
    return "\n".join(lines)


def model_output_path(model_root: Path, cfg: dict[str, object], *, with_sink: bool) -> Path:
    filename_key = "with_sink_name" if with_sink else "model_name"
    return model_root.joinpath(*cfg["model_subdir"]) / str(cfg[filename_key])


def build_rules(case_key: str) -> list[Rule]:
    case_type = CASE_DEFS[case_key]["case_type"]
    rules: list[Rule] = []
    for transition_family, source_output, target_output in TRANSITION_FAMILIES:
        for input_label in CASE_DEFS[case_key]["input_labels"]:
            antecedent = f"output = {source_output} & input_label = {input_label}"
            consequent = f"output = {target_output}"
            rule_id = f"{transition_family}__{input_label}"
            rules.append(
                Rule(
                    rule_id=rule_id,
                    case_type=case_type,
                    transition_family=transition_family,
                    input_label=input_label,
                    antecedent=antecedent,
                    consequent=consequent,
                    source_output=source_output,
                    target_output=target_output,
                    main_spec=(
                        f"SPEC AG(({antecedent}) -> AX(output = {source_output} | {consequent}))"
                    ),
                    ef_spec=f"SPEC EF({antecedent})",
                    ltl_spec=f"LTLSPEC G(({antecedent}) -> X({consequent}))",
                )
            )
    return rules


def extract_declared_input_labels(model_text: str) -> list[str]:
    match = INPUT_LABEL_RE.search(model_text)
    if not match:
        raise ValueError("Could not find input_label enumeration in model.")
    return [token.strip() for token in match.group(1).split(",") if token.strip()]


def build_checker_model_text(model_text: str, declared_labels: list[str]) -> str:
    label_set_literal = "{" + ", ".join(declared_labels) + "}"
    ivar_match = IVAR_BLOCK_RE.search(model_text)
    if not ivar_match:
        raise ValueError("Could not find the IVAR input_label block in model.")
    rewritten = IVAR_BLOCK_RE.sub(
        "VAR\n"
        f"  input_label : {label_set_literal};\n",
        model_text,
        count=1,
    )
    init_match = INIT_STATE_RE.search(rewritten)
    if not init_match:
        raise ValueError("Could not find init(state) in model ASSIGN block.")
    insertion = (
        init_match.group(1)
        + f"\n  init(input_label) := {label_set_literal};"
        + f"\n  next(input_label) := {label_set_literal};"
    )
    return INIT_STATE_RE.sub(insertion, rewritten, count=1)


def run_nusmv(nusmv_path: str, checker_path: Path) -> str:
    result = subprocess.run(
        [nusmv_path, str(checker_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout
    if result.stderr:
        output += ("\n" if output else "") + result.stderr
    if result.returncode != 0:
        raise RuntimeError(f"NuSMV failed for {checker_path} with exit code {result.returncode}")
    return output


def parse_spec_results(raw_output: str) -> list[str]:
    results: list[str] = []
    for line in raw_output.splitlines():
        match = SPEC_RESULT_RE.match(line.strip())
        if match:
            results.append(match.group(1).upper())
    return results


def normalize_spec_text(spec_text: str) -> str:
    text = spec_text.strip()
    if text.upper().startswith("SPEC "):
        text = text[5:]
    if text.upper().startswith("LTLSPEC "):
        text = text[8:]
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[()]+", "", text)


def parse_spec_blocks(raw_output: str) -> dict[str, list[dict[str, object]]]:
    blocks: dict[str, list[dict[str, object]]] = {}
    current_key: str | None = None
    current_result: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_key is None or current_result is None:
            return
        blocks.setdefault(current_key, []).append(
            {"result": current_result, "lines": list(current_lines)}
        )

    for line in raw_output.splitlines():
        match = SPEC_LINE_RE.match(line.strip())
        if match:
            flush()
            current_key = normalize_spec_text(match.group(1))
            current_result = match.group(2).upper()
            current_lines = [line]
            continue
        if current_key is not None:
            current_lines.append(line)
    flush()
    return blocks


def parse_output_value_aliases(model_text: str) -> dict[str, str]:
    value_to_alias: dict[str, str] = {}
    for alias, raw_value in OUTPUT_ALIAS_RE.findall(model_text):
        value_to_alias[raw_value.strip()] = alias
    return value_to_alias


def resolve_output_alias(raw_value: str | None, value_to_alias: dict[str, str]) -> str:
    if raw_value is None:
        return ""
    return value_to_alias.get(raw_value.strip(), raw_value.strip())


def parse_counterexample_states(block_lines: list[str]) -> list[dict[str, str]]:
    states: list[dict[str, str]] = []
    previous: dict[str, str] = {}
    current: dict[str, str] | None = None
    for line in block_lines:
        if STATE_HEADER_RE.match(line):
            if current is not None:
                states.append(current)
                previous = current
            current = dict(previous)
            continue
        if current is None:
            continue
        match = ASSIGNMENT_RE.match(line)
        if match:
            current[match.group(1)] = match.group(2).strip()
    if current is not None:
        states.append(current)
    return states


def extract_ltl_failure_details(
    rule: Rule,
    *,
    spec_blocks: dict[str, list[dict[str, object]]],
    value_to_alias: dict[str, str],
) -> tuple[str, str, str]:
    spec_key = normalize_spec_text(rule.ltl_spec)
    blocks = spec_blocks.get(spec_key, [])
    false_block = next((block for block in blocks if block["result"] == "FALSE"), None)
    if false_block is None:
        return (
            "UNKNOWN",
            "UNKNOWN",
            "Rule failed, but no matching raw NuSMV counterexample block was found.",
        )

    states = parse_counterexample_states(false_block["lines"])
    for index in range(len(states) - 1):
        current = states[index]
        nxt = states[index + 1]
        if current.get("input_label") != rule.input_label:
            continue
        current_output = resolve_output_alias(current.get("output"), value_to_alias)
        if current_output != rule.source_output:
            continue
        next_output = resolve_output_alias(nxt.get("output"), value_to_alias)
        next_state = nxt.get("state", "UNKNOWN")
        if next_output and next_output != rule.target_output:
            sink_hit = (
                "TRUE"
                if next_output == "out_sink" or next_state == "sink"
                else "FALSE"
            )
            why = (
                f"Counterexample shows {current.get('state', 'UNKNOWN')} with {rule.source_output} "
                f"under {rule.input_label}, then {next_state} with next output {next_output}, "
                f"not equal to required next output {rule.target_output}."
            )
            return next_output, sink_hit, why

    return (
        "UNKNOWN",
        "UNKNOWN",
        "Rule failed, but the exact violating successor output was not extracted cleanly from the counterexample.",
    )


def extract_main_failure_details(
    rule: Rule,
    *,
    spec_blocks: dict[str, list[dict[str, object]]],
    value_to_alias: dict[str, str],
) -> tuple[str, str]:
    allowed = {rule.source_output, rule.target_output}
    spec_key = normalize_spec_text(rule.main_spec)
    blocks = spec_blocks.get(spec_key, [])
    false_block = next((block for block in blocks if block["result"] == "FALSE"), None)
    if false_block is None:
        return (
            "UNKNOWN",
            "Rule is FALSE, but no matching raw NuSMV counterexample block was found.",
        )

    states = parse_counterexample_states(false_block["lines"])
    for index in range(len(states) - 1):
        current = states[index]
        nxt = states[index + 1]
        if current.get("input_label") != rule.input_label:
            continue
        current_output = resolve_output_alias(current.get("output"), value_to_alias)
        if current_output != rule.source_output:
            continue
        next_output = resolve_output_alias(nxt.get("output"), value_to_alias)
        if next_output and next_output not in allowed:
            current_state = current.get("state", "UNKNOWN")
            next_state = nxt.get("state", "UNKNOWN")
            return (
                next_output,
                f"Counterexample shows {current_state} with {rule.source_output} under {rule.input_label}, "
                f"then {next_state} with next output {next_output}, outside allowed next outputs "
                f"{{{rule.source_output}, {rule.target_output}}}.",
            )
    return (
        "UNKNOWN",
        "Rule is FALSE, but the exact violating successor output was not extracted from the raw NuSMV counterexample.",
    )


def classify_ef(declared: bool, main_result: str, ef_result: str) -> str:
    if not declared:
        return "ND"
    if main_result == "FALSE":
        return "REAL_FALSE"
    if main_result != "TRUE":
        return "ND"
    if ef_result == "FALSE":
        return "VACUOUS_TRUE_EF"
    return "REAL_TRUE"




def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

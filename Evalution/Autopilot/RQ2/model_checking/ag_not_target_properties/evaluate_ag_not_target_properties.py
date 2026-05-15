#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import pydot


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Results").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate Autopilot project root from {start}")

PROJECT_ROOT = find_project_root(Path(__file__))
ROOT = PROJECT_ROOT
SMV_ROOT = PROJECT_ROOT / "Results" / "RQ2" / "Autopilot"
OUT_DIR = SMV_ROOT / "summaries" / "ag_not_target_property_check"
CHECKER_DIR = OUT_DIR / "generated_checker_models"

ASCENT_INPUTS = [
    ("(L,L)", "p_low_t_low"),
    ("(L,M)", "p_low_t_med"),
    ("(L,H)", "p_low_t_high"),
]

DESCENT_INPUTS = [
    ("(M,L)", "p_med_t_low"),
    ("(H,L)", "p_high_t_low"),
    ("(M,M)", "p_med_t_med"),
    ("(H,M)", "p_high_t_med"),
    ("(H,H)", "p_high_t_high"),
    ("(M,H)", "p_med_t_high"),
]

RULES = [
    ("CR_not_CA", "out_critical", "out_caution"),
    ("CA_not_N", "out_caution", "out_nominal"),
]

CSV_FIELDS = [
    "command",
    "rule",
    "input_label",
    "gsm_ag_result",
    "gsm_ef_result",
    "gsm_final_result",
    "pta_ag_result",
    "pta_ef_result",
    "pta_final_result",
    "same_result",
]

INPUT_LABEL_RE = re.compile(r"\binput_label\s*:\s*\{([^}]*)\}\s*;", re.MULTILINE | re.DOTALL)
IVAR_INPUT_RE = re.compile(
    r"\bIVAR\s+input_label\s*:\s*\{([^}]*)\}\s*;\s+VAR\b",
    re.MULTILINE | re.DOTALL,
)
INIT_STATE_INSERT_RE = re.compile(r"(\binit\(state\)\s*:=\s*[^;]+;)")
INIT_STATE_PARSE_RE = re.compile(r"\binit\(state\)\s*:=\s*([A-Za-z_][A-Za-z0-9_]*)\s*;")
STATE_OUTPUT_RE = re.compile(
    r"\bstate\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(out_[A-Za-z0-9_]+)\s*;"
)
SMV_TRANSITION_RE = re.compile(
    r"\bstate\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*&\s*"
    r"input_label\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
    r"next\(state\)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*;"
)
SPEC_LINE_RE = re.compile(r"^\s*(CTLSPEC|SPEC|LTLSPEC)\b", re.IGNORECASE)
ASSIGN_SECTION_RE = re.compile(r"\nASSIGN\b")

GENERATED_DIR_NAMES = {
    "generated_checkers",
    "generated_checker_models",
    "ag_not_target_property_check",
    "r1_ctl_not_selfloop_check",
}


@dataclass(frozen=True)
class ModelInfo:
    family: str
    command: str
    path: Path
    declared_labels: tuple[str, ...]


@dataclass(frozen=True)
class RuleCheck:
    command: str
    rule: str
    input_label: str
    source_output: str
    forbidden_output: str
    ag_formula: str
    ef_formula: str


@dataclass(frozen=True)
class Edge:
    source_state: str
    input_label: str
    next_state: str
    source_output: str
    next_output: str


@dataclass(frozen=True)
class RelationIndex:
    initial_state: str
    reachable_states: frozenset[str]
    state_output: dict[str, str]
    edges: tuple[Edge, ...]
    edges_by_state_input: dict[tuple[str, str], tuple[Edge, ...]]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def infer_command(path: Path) -> str | None:
    parts = {part.lower() for part in path.parts}
    if "ascend" in parts or "ascent" in parts:
        return "Ascent"
    if "descend" in parts or "descent" in parts:
        return "Descent"
    return None


def infer_family(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if "pta" in parts or path.name.lower().startswith("pta_"):
        return "PTA"
    return "GSM"


def inputs_for_command(command: str) -> list[tuple[str, str]]:
    if command == "Ascent":
        return ASCENT_INPUTS
    if command == "Descent":
        return DESCENT_INPUTS
    raise ValueError(f"Unknown command: {command}")


def clean_dot_value(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text.strip()


def category_to_output(raw: str) -> str:
    text = clean_dot_value(raw).replace("\\n", "\n").replace("out_", "").strip()
    lowered = text.lower()
    if "critical" in lowered:
        return "out_critical"
    if "caution" in lowered:
        return "out_caution"
    if "nominal" in lowered:
        return "out_nominal"
    if "none" in lowered:
        return "out_none"
    return ""


def normalize_input_label(raw: str) -> str:
    text = clean_dot_value(raw)
    text = text.replace("\\n", " ").replace("\n", " ").strip()
    if not text:
        return ""
    if re.fullmatch(r"(p|t)_(low|med|high)(_(p|t)_(low|med|high))?", text):
        return text
    found = re.findall(r"\b([pt])\s*:\s*(low|med|high)\b", text, flags=re.IGNORECASE)
    if found:
        return "_".join(f"{var.lower()}_{level.lower()}" for var, level in found)
    text = text.replace(":", "_")
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"__+", "_", text)
    return text.lower()


def extract_declared_input_labels(model_text: str) -> tuple[str, ...]:
    match = INPUT_LABEL_RE.search(model_text)
    if not match:
        return ()
    return tuple(token.strip() for token in match.group(1).split(",") if token.strip())


def discover_models() -> tuple[list[ModelInfo], list[tuple[str, str]]]:
    models: list[ModelInfo] = []
    skipped: list[tuple[str, str]] = []

    for path in sorted(SMV_ROOT.rglob("*.smv")):
        if is_under(path, OUT_DIR):
            continue
        if GENERATED_DIR_NAMES.intersection({part.lower() for part in path.parts}):
            skipped.append((rel(path), "generated checker file"))
            continue
        if path.name.lower().startswith("checker_") or "check_results" in {part.lower() for part in path.parts}:
            skipped.append((rel(path), "legacy checker/result file"))
            continue

        text = read_text(path)
        if "MODULE main" not in text or "input_label" not in text or "output" not in text:
            skipped.append((rel(path), "not a compatible NuSMV automaton"))
            continue

        command = infer_command(path)
        if command is None:
            skipped.append((rel(path), "could not infer Ascent/Descent from path"))
            continue

        declared_labels = extract_declared_input_labels(text)
        required_labels = {label for _, label in inputs_for_command(command)}
        missing_labels = sorted(required_labels.difference(declared_labels))
        if missing_labels:
            skipped.append((rel(path), "not Top-2 RQ2 model; missing " + ", ".join(missing_labels)))
            continue

        required_outputs = {"out_critical", "out_caution", "out_nominal"}
        missing_outputs = sorted(output for output in required_outputs if output not in text)
        if missing_outputs:
            skipped.append((rel(path), "missing output aliases " + ", ".join(missing_outputs)))
            continue

        models.append(
            ModelInfo(
                family=infer_family(path),
                command=command,
                path=path,
                declared_labels=declared_labels,
            )
        )

    return models, skipped


def choose_models(models: list[ModelInfo]) -> dict[tuple[str, str], ModelInfo]:
    selected: dict[tuple[str, str], ModelInfo] = {}
    for model in models:
        key = (model.family, model.command)
        current = selected.get(key)
        if current is None:
            selected[key] = model
            continue
        if "generated_models" in str(model.path) and "generated_models" not in str(current.path):
            selected[key] = model
    return selected


def ag_formula(source_output: str, forbidden_output: str, input_label: str) -> str:
    return (
        f"CTLSPEC AG((output = {source_output} & input_label = {input_label}) -> "
        f"AX(!(output = {forbidden_output})));"
    )


def ef_formula(source_output: str, input_label: str) -> str:
    return f"CTLSPEC EF(output = {source_output} & input_label = {input_label});"


def build_rule_checks(command: str) -> list[RuleCheck]:
    checks: list[RuleCheck] = []
    for _, input_label in inputs_for_command(command):
        for rule, source_output, forbidden_output in RULES:
            checks.append(
                RuleCheck(
                    command=command,
                    rule=rule,
                    input_label=input_label,
                    source_output=source_output,
                    forbidden_output=forbidden_output,
                    ag_formula=ag_formula(source_output, forbidden_output, input_label),
                    ef_formula=ef_formula(source_output, input_label),
                )
            )
    return checks


def strip_existing_specs(model_text: str) -> str:
    lines = []
    for line in model_text.splitlines():
        if SPEC_LINE_RE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines).rstrip() + "\n"


def parse_relation(model_path: Path) -> RelationIndex:
    model_text = read_text(model_path)
    state_output = dict(STATE_OUTPUT_RE.findall(model_text))
    init_match = INIT_STATE_PARSE_RE.search(model_text)
    initial_state = init_match.group(1) if init_match else ""

    edges: list[Edge] = []
    graph: dict[str, set[str]] = defaultdict(set)
    edges_by_state_input_lists: dict[tuple[str, str], list[Edge]] = defaultdict(list)

    for source_state, input_label, next_state in SMV_TRANSITION_RE.findall(model_text):
        edge = Edge(
            source_state=source_state,
            input_label=input_label,
            next_state=next_state,
            source_output=state_output.get(source_state, ""),
            next_output=state_output.get(next_state, ""),
        )
        edges.append(edge)
        graph[source_state].add(next_state)
        edges_by_state_input_lists[(source_state, input_label)].append(edge)

    if not initial_state and "q0" in state_output:
        initial_state = "q0"
    if not initial_state and "s0" in state_output:
        initial_state = "s0"
    if not initial_state and edges:
        initial_state = edges[0].source_state

    reachable: set[str] = set()
    if initial_state:
        reachable.add(initial_state)
        queue: deque[str] = deque([initial_state])
        while queue:
            state = queue.popleft()
            for next_state in graph.get(state, set()):
                if next_state not in reachable:
                    reachable.add(next_state)
                    queue.append(next_state)

    edges_by_state_input = {
        key: tuple(value)
        for key, value in edges_by_state_input_lists.items()
    }

    return RelationIndex(
        initial_state=initial_state,
        reachable_states=frozenset(reachable),
        state_output=state_output,
        edges=tuple(edges),
        edges_by_state_input=edges_by_state_input,
    )


def pta_dot_path(command: str) -> Path:
    if command == "Ascent":
        return SMV_ROOT / "ascend" / "PTA" / "pta_models" / "MELA" / "pitchwheel_throttle" / "pta_moore.dot"
    if command == "Descent":
        return SMV_ROOT / "descend" / "PTA" / "pta_models" / "MELA" / "pitchwheel_throttle" / "pta_moore.dot"
    raise ValueError(f"Unknown command: {command}")


def parse_pta_dot_relation(dot_path: Path) -> RelationIndex:
    graphs = pydot.graph_from_dot_file(str(dot_path))
    if not graphs:
        raise RuntimeError(f"Could not parse PTA DOT file: {dot_path}")

    graph = graphs[0]
    state_output: dict[str, str] = {}
    initial_state = ""

    for node in graph.get_nodes():
        name = clean_dot_value(node.get_name())
        if not name or name in {"node", "graph", "edge"}:
            continue
        label = clean_dot_value(node.get_label())
        state_output[name] = category_to_output(label)

    edges: list[Edge] = []
    graph_edges: dict[str, set[str]] = defaultdict(set)
    edges_by_state_input_lists: dict[tuple[str, str], list[Edge]] = defaultdict(list)

    for dot_edge in graph.get_edges():
        source_state = clean_dot_value(dot_edge.get_source())
        next_state = clean_dot_value(dot_edge.get_destination())

        if source_state.startswith("__start"):
            initial_state = next_state
            continue
        if next_state.startswith("__start"):
            continue

        input_label = normalize_input_label(clean_dot_value(dot_edge.get_label()))
        if not input_label:
            continue

        edge = Edge(
            source_state=source_state,
            input_label=input_label,
            next_state=next_state,
            source_output=state_output.get(source_state, ""),
            next_output=state_output.get(next_state, ""),
        )
        edges.append(edge)
        graph_edges[source_state].add(next_state)
        edges_by_state_input_lists[(source_state, input_label)].append(edge)

    if not initial_state and "q0" in state_output:
        initial_state = "q0"
    if not initial_state and edges:
        initial_state = edges[0].source_state

    reachable: set[str] = set()
    if initial_state:
        reachable.add(initial_state)
        queue: deque[str] = deque([initial_state])
        while queue:
            state = queue.popleft()
            for next_state in graph_edges.get(state, set()):
                if next_state not in reachable:
                    reachable.add(next_state)
                    queue.append(next_state)

    edges_by_state_input = {
        key: tuple(value)
        for key, value in edges_by_state_input_lists.items()
    }

    return RelationIndex(
        initial_state=initial_state,
        reachable_states=frozenset(reachable),
        state_output=state_output,
        edges=tuple(edges),
        edges_by_state_input=edges_by_state_input,
    )


def classify_not_target(index: RelationIndex, check: RuleCheck) -> dict[str, str]:
    matching_edges = matching_edges_for_check(index, check)

    ag_result = (
        "FALSE"
        if any(edge.next_output == check.forbidden_output for edge in matching_edges)
        else "TRUE"
    )
    ef_result = "TRUE" if matching_edges else "FALSE"

    if ag_result == "FALSE":
        final = "VIOLATION"
    elif ef_result == "FALSE":
        final = "VACUOUS"
    else:
        final = "PASS"

    return {
        "command": check.command,
        "rule": check.rule,
        "input_label": check.input_label,
        "ag_result": ag_result,
        "ef_result": ef_result,
        "final_result": final,
    }


def matching_edges_for_check(index: RelationIndex, check: RuleCheck) -> list[Edge]:
    matching_edges: list[Edge] = []
    for edge in index.edges:
        if edge.source_state not in index.reachable_states:
            continue
        if edge.source_output != check.source_output:
            continue
        if edge.input_label != check.input_label:
            continue
        matching_edges.append(edge)
    return matching_edges


def unique_join(values: list[str]) -> str:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return "; ".join(unique)


def enabled_definition(index: RelationIndex) -> str:
    seen: set[tuple[str, str]] = set()
    terms: list[str] = []
    for edge in index.edges:
        key = (edge.source_state, edge.input_label)
        if key in seen:
            continue
        seen.add(key)
        terms.append(f"(state = {edge.source_state} & input_label = {edge.input_label})")

    if not terms:
        return "  enabled_input_pair := FALSE;\n"

    joined = "\n    | ".join(terms)
    return f"  enabled_input_pair :=\n    {joined};\n"


def insert_enabled_definition(model_text: str, index: RelationIndex) -> str:
    if "enabled_input_pair" in model_text:
        return model_text

    definition = enabled_definition(index) + "\n"
    if ASSIGN_SECTION_RE.search(model_text):
        return ASSIGN_SECTION_RE.sub("\n" + definition + "ASSIGN", model_text, count=1)

    return model_text.rstrip() + "\n\nDEFINE\n" + definition


def checker_text(model: ModelInfo, checks: list[RuleCheck], index: RelationIndex) -> str:
    text = strip_existing_specs(read_text(model.path))
    label_set = "{" + ", ".join(model.declared_labels) + "}"

    if IVAR_INPUT_RE.search(text):
        text = IVAR_INPUT_RE.sub(f"VAR\n  input_label : {label_set};\n", text, count=1)

    if "init(input_label)" not in text or "next(input_label)" not in text:
        init_match = INIT_STATE_INSERT_RE.search(text)
        if not init_match:
            raise ValueError(f"Could not find init(state) in {rel(model.path)}")
        replacement = init_match.group(1)
        if "init(input_label)" not in text:
            replacement += f"\n  init(input_label) := {label_set};"
        if "next(input_label)" not in text:
            replacement += f"\n  next(input_label) := {label_set};"
        text = INIT_STATE_INSERT_RE.sub(replacement, text, count=1)

    text = insert_enabled_definition(text, index)

    lines = [
        "",
        "-- RQ2 AG not-target checks: non-corrective input should not improve",
        "-- The INVAR excludes alphabet-only state/input pairs introduced by the checker copy.",
        "INVAR enabled_input_pair",
    ]
    for check in checks:
        lines.append(f"-- {check.rule}__{check.input_label} AG")
        lines.append(check.ag_formula)
        lines.append(f"-- {check.rule}__{check.input_label} EF")
        lines.append(check.ef_formula)
    return text.rstrip() + "\n" + "\n".join(lines) + "\n"


def checker_path(model: ModelInfo) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", rel(model.path).replace("/", "__"))
    return CHECKER_DIR / f"{model.family.lower()}__{model.command.lower()}__{safe}"


def evaluate_model(model: ModelInfo) -> dict[tuple[str, str, str], dict[str, str]]:
    checks = build_rule_checks(model.command)
    index = parse_relation(model.path)

    path = checker_path(model)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(checker_text(model, checks, index), encoding="utf-8")

    rows: dict[tuple[str, str, str], dict[str, str]] = {}
    for check in checks:
        result = classify_not_target(index, check)
        rows[(check.command, check.rule, check.input_label)] = result
    return rows


def evaluate_pta_dot(command: str) -> dict[tuple[str, str, str], dict[str, str]]:
    checks = build_rule_checks(command)
    dot_path = pta_dot_path(command)
    index = parse_pta_dot_relation(dot_path)

    rows: dict[tuple[str, str, str], dict[str, str]] = {}
    for check in checks:
        result = classify_not_target(index, check)
        rows[(check.command, check.rule, check.input_label)] = result
    return rows


def empty_side() -> dict[str, str]:
    return {
        "ag_result": "MISSING",
        "ef_result": "MISSING",
        "final_result": "MISSING",
    }


def combined_rows(
    gsm_results: dict[tuple[str, str, str], dict[str, str]],
    pta_results: dict[tuple[str, str, str], dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    order: list[tuple[str, str, str]] = []
    for command, inputs in (("Ascent", ASCENT_INPUTS), ("Descent", DESCENT_INPUTS)):
        for _, input_label in inputs:
            for rule, _, _ in RULES:
                order.append((command, rule, input_label))

    for key in order:
        gsm = gsm_results.get(key, empty_side())
        pta = pta_results.get(key, empty_side())
        command, rule, input_label = key
        gsm_final = gsm["final_result"]
        pta_final = pta["final_result"]
        rows.append(
            {
                "command": command,
                "rule": rule,
                "input_label": input_label,
                "gsm_ag_result": gsm["ag_result"],
                "gsm_ef_result": gsm["ef_result"],
                "gsm_final_result": gsm_final,
                "pta_ag_result": pta["ag_result"],
                "pta_ef_result": pta["ef_result"],
                "pta_final_result": pta_final,
                "same_result": "YES" if gsm_final == pta_final else "NO",
            }
        )
    return rows


def write_report(
    *,
    path: Path,
    selected: dict[tuple[str, str], ModelInfo],
    skipped: list[tuple[str, str]],
    rows: list[dict[str, str]],
) -> None:
    gsm_counts = Counter(row["gsm_final_result"] for row in rows)
    pta_counts = Counter(row["pta_final_result"] for row in rows)
    same_counts = Counter(row["same_result"] for row in rows)

    lines = [
        "# RQ2 AG Not-Target Report",
        "",
        "RQ2 checks non-corrective inputs and requires that outputs do not improve.",
        "",
        "Important correction: GSM results are computed from the reachable GSM SMV transition relation, and PTA results are computed from the reachable PTA DOT transition relation. This avoids the PTA bug where making `input_label` a free checker variable makes alphabet-only labels look reachable in EF checks.",
        "",
        "Temporary checked NuSMV files are still written under `generated_checker_models` for audit, but the CSV result columns use parsed transition tables as the source of truth.",
        "",
        "The CSV includes PTA DOT details for each row: matching transition count, source states, transition labels, next states, and next outputs.",
        "",
        "CTL rules used:",
        "",
        "`CTLSPEC AG((output = out_critical & input_label = INPUT) -> AX(!(output = out_caution)));`",
        "",
        "`CTLSPEC AG((output = out_caution & input_label = INPUT) -> AX(!(output = out_nominal)));`",
        "",
        "Vacuity check:",
        "",
        "`CTLSPEC EF(output = source_output & input_label = INPUT);`",
        "",
        "Final-result mapping: AG TRUE + EF TRUE = PASS; AG TRUE + EF FALSE = VACUOUS; AG FALSE = VIOLATION.",
        "",
        "## Models Checked",
        "",
    ]

    for family in ("GSM", "PTA"):
        for command in ("Ascent", "Descent"):
            model = selected.get((family, command))
            if model:
                lines.append(f"- {family} {command}: `{rel(model.path)}`")
            else:
                lines.append(f"- {family} {command}: MISSING")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Rows: {len(rows)}",
            f"- GSM PASS: {gsm_counts.get('PASS', 0)}",
            f"- GSM VIOLATION: {gsm_counts.get('VIOLATION', 0)}",
            f"- GSM VACUOUS: {gsm_counts.get('VACUOUS', 0)}",
            f"- PTA PASS: {pta_counts.get('PASS', 0)}",
            f"- PTA VIOLATION: {pta_counts.get('VIOLATION', 0)}",
            f"- PTA VACUOUS: {pta_counts.get('VACUOUS', 0)}",
            f"- Same final result: {same_counts.get('YES', 0)}",
            f"- Different final result: {same_counts.get('NO', 0)}",
            "",
            "## Results",
            "",
            "| Command | Rule | Input | GSM | PTA | Same |",
            "|---|---|---|---|---|---|",
        ]
    )

    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["command"],
                    row["rule"],
                    f'`{row["input_label"]}`',
                    row["gsm_final_result"],
                    row["pta_final_result"],
                    row["same_result"],
                ]
            )
            + " |"
        )

    if skipped:
        lines.extend(["", "## Skipped `.smv` Files", ""])
        for file_name, reason in skipped:
            lines.append(f"- `{file_name}`: {reason}")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKER_DIR.mkdir(parents=True, exist_ok=True)

    discovered, skipped = discover_models()
    selected = choose_models(discovered)

    all_results: dict[str, dict[tuple[str, str, str], dict[str, str]]] = {"GSM": {}, "PTA": {}}
    for family in ("GSM", "PTA"):
        for command in ("Ascent", "Descent"):
            model = selected.get((family, command))
            if not model:
                continue
            # Always write the temporary checker copy. For PTA, use the DOT
            # transition table for the result columns below.
            smv_results = evaluate_model(model)
            if family == "PTA":
                all_results[family].update(evaluate_pta_dot(command))
            else:
                all_results[family].update(smv_results)

    rows = combined_rows(all_results["GSM"], all_results["PTA"])
    write_csv(OUT_DIR / "rq2_ag_gsm_pta_results.csv", rows)
    write_report(
        path=OUT_DIR / "rq2_ag_report.md",
        selected=selected,
        skipped=skipped,
        rows=rows,
    )

    gsm_counts = Counter(row["gsm_final_result"] for row in rows)
    pta_counts = Counter(row["pta_final_result"] for row in rows)
    same_counts = Counter(row["same_result"] for row in rows)
    print(f"Wrote {OUT_DIR / 'rq2_ag_gsm_pta_results.csv'}")
    print(f"Wrote {OUT_DIR / 'rq2_ag_report.md'}")
    print(
        "GSM: "
        f"PASS={gsm_counts.get('PASS', 0)} "
        f"VIOLATION={gsm_counts.get('VIOLATION', 0)} "
        f"VACUOUS={gsm_counts.get('VACUOUS', 0)}"
    )
    print(
        "PTA: "
        f"PASS={pta_counts.get('PASS', 0)} "
        f"VIOLATION={pta_counts.get('VIOLATION', 0)} "
        f"VACUOUS={pta_counts.get('VACUOUS', 0)}"
    )
    print(f"Same final result rows: {same_counts.get('YES', 0)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import json
import re
import shutil
import subprocess

NODE_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_\-]*)\s*\[.*label="([^"]*)".*\]\s*;\s*$')
EDGE_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_\-]*)\s*->\s*([A-Za-z_][A-Za-z0-9_\-]*)\s*\[.*label="([^"]*)".*\]\s*;\s*$')

PROPS = {
    "P1": ("Attack", "Safe", ["Warning", "TWarning"]),
    "P2": ("Attack", "Warning", ["Alert", "TAlert"]),
    "P3": ("Attack", "Alert", ["Alert", "TAlert"]),
    "P4": ("Normal", "Safe", ["Safe"]),
    "P5": ("Normal", "Warning", ["Safe"]),
    "P6": ("Normal", "Alert", ["Warning", "TWarning"]),
}

LEVELS = [("Low", "L"), ("Med", "M"), ("High", "H")]
TOP2 = [
    ("LU", "LF"), ("LU", "MF"), ("LU", "HF"),
    ("MU", "LF"), ("MU", "MF"), ("MU", "HF"),
    ("HU", "LF"), ("HU", "MF"), ("HU", "HF"),
]

ALL_IDS_OUTPUTS = ["Alert", "None", "Safe", "TAlert", "TWarning", "Warning"]
NO_INPUT = "NO_INPUT"

RESERVED = {
    "TRUE", "FALSE", "MODULE", "VAR", "IVAR", "DEFINE", "TRANS", "ASSIGN",
    "INVAR", "SPEC", "CTLSPEC", "LTLSPEC", "case", "esac", "init", "next",
    "in", "union", "mod", "process", "array", "of", "boolean", "integer", "word",
}


@dataclass
class Model:
    path: Path
    filename: str
    model_type: str
    dataset: str
    config: str
    nodes: dict[str, str]
    edges: list[tuple[str, str, str]]
    init: str


def safe_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name.strip())
    if not s:
        raise ValueError("Empty identifier after sanitization.")
    if not re.match(r"[A-Za-z_]", s):
        s = "_" + s
    if s in RESERVED:
        s = s + "_id"
    return s


def sort_state(s: str):
    m = re.match(r"([A-Za-z_]+)(\d+)$", s)
    return (m.group(1), int(m.group(2))) if m else (s, 0)


def parse_meta(filename: str):
    lower = filename.lower()
    model_type = "Moore" if lower.startswith("moore") else "PTA"
    dataset = "DDoS" if "ddos" in lower else "DoS5"
    config = "Top-2" if "top" in lower else ("1st" if "1st" in lower else ("2nd" if "2nd" in lower else "UNKNOWN"))
    return model_type, dataset, config


def parse_dot(path: Path) -> Model:
    nodes: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    init = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("digraph") or line in {"{", "}"}:
            continue

        edge = EDGE_RE.match(line)
        if edge:
            src, dst, label = edge.groups()
            if src == "__start0" and label == "":
                init = dst
            elif src != "__start0" and label != "":
                edges.append((src, label, dst))
            continue

        node = NODE_RE.match(line)
        if node:
            node_id, label = node.groups()
            if node_id != "__start0":
                output = label.split("|", 1)[1].strip() if "|" in label else label.strip()
                nodes[node_id] = output

    if init is None:
        raise ValueError(f"Missing __start0 initial edge in {path}")

    for src, _, dst in edges:
        if src not in nodes:
            raise ValueError(f"Transition source {src!r} has no node label in {path}")
        if dst not in nodes:
            raise ValueError(f"Transition destination {dst!r} has no node label in {path}")

    model_type, dataset, config = parse_meta(path.name)
    return Model(path, path.name, model_type, dataset, config, nodes, edges, init)


def expected_inputs(model: Model):
    if model.config == "Top-2":
        return [(f"({u},{f})", f"D_{u}_{f}", f"N_{u}_{f}") for u, f in TOP2]
    return [(name, f"D{letter}", f"N{letter}") for name, letter in LEVELS]


def property_inputs(model: Model) -> set[str]:
    result: set[str] = set()
    for _, attack_input, normal_input in expected_inputs(model):
        result.add(attack_input)
        result.add(normal_input)
    return result


def reachable_states(model: Model):
    adj = defaultdict(list)
    for src, _, dst in model.edges:
        adj[src].append(dst)
    seen, queue = {model.init}, deque([model.init])
    while queue:
        state = queue.popleft()
        for dst in adj.get(state, []):
            if dst not in seen:
                seen.add(dst)
                queue.append(dst)
    return seen


def evaluate(model: Model):
    trans = defaultdict(list)
    for src, label, dst in model.edges:
        trans[(src, label)].append(dst)

    reachable = reachable_states(model)
    rows = []

    for input_level, attack_input, normal_input in expected_inputs(model):
        for pid, (kind, src_output, dst_outputs) in PROPS.items():
            input_label = attack_input if kind == "Attack" else normal_input
            antecedent_edges, violations = [], []

            for state in sorted(reachable, key=sort_state):
                if model.nodes.get(state) != src_output:
                    continue
                for dst in trans.get((state, input_label), []):
                    dst_output = model.nodes.get(dst)
                    antecedent_edges.append((state, input_label, dst, dst_output))
                    if dst_output not in dst_outputs:
                        violations.append((state, input_label, dst, dst_output))

            ef = bool(antecedent_edges)
            ag = not bool(violations)
            symbol = r"\checkmark" if ag and ef else ("v" if ag and not ef else r"$\times$")
            rows.append({
                "model_type": model.model_type,
                "dot_filename": model.filename,
                "learning_set": model.dataset,
                "configuration": model.config,
                "input_level_or_top2_pair": input_level,
                "property_id": pid,
                "input_label": input_label,
                "AG_result": "TRUE" if ag else "FALSE",
                "EF_antecedent_result": "TRUE" if ef else "FALSE",
                "final_symbol": symbol,
                "antecedent_edges_count": len(antecedent_edges),
                "violation_count": len(violations),
                "violation_examples": "; ".join(f"{s} --{i}--> {d}({o})" for s, i, d, o in violations[:5]),
            })
    return rows


def disjunction(terms: list[str]) -> str:
    if not terms:
        return "FALSE"
    if len(terms) == 1:
        return terms[0]
    return "(" + " | ".join(terms) + ")"


def generate_smv(model: Model):
    states = sorted(model.nodes, key=sort_state)

    # Inputs used by properties are included so all CTL specs are well typed.
    # Input is a VAR, not IVAR, because NuSMV does not allow IVARs in CTL specs.
    dot_inputs = {label for _, label, _ in model.edges}
    all_inputs = sorted(dot_inputs | property_inputs(model) | {NO_INPUT})

    outputs = sorted(set(model.nodes.values()) | set(ALL_IDS_OUTPUTS))

    state_map = {s: safe_name(s) for s in states}
    input_map = {i: safe_name(i) for i in all_inputs}
    output_map = {o: safe_name(o) for o in outputs}

    # Detect accidental collisions after sanitization.
    for title, mapping in (("state", state_map), ("input", input_map), ("output", output_map)):
        inverse = {}
        for original, safe in mapping.items():
            if safe in inverse and inverse[safe] != original:
                raise ValueError(f"{title} names {inverse[safe]!r} and {original!r} both map to {safe!r}")
            inverse[safe] = original

    enabled_by_state: dict[str, set[str]] = defaultdict(set)
    for src, label, _ in model.edges:
        enabled_by_state[src].add(label)

    lines: list[str] = []
    lines.append("MODULE main")
    lines.append("")
    lines.append("VAR")
    lines.append("  state : {" + ", ".join(state_map[s] for s in states) + "};")
    lines.append("  input : {" + ", ".join(input_map[i] for i in all_inputs) + "};")
    lines.append("")
    lines.append("DEFINE")

    # Output labels are numeric constants. This matches the style in the user's
    # existing converter and avoids undefined symbolic constants in NuSMV 2.6.
    for idx, out in enumerate(outputs):
        lines.append(f"  {output_map[out]} := {idx};")
    lines.append("")
    lines.append("  output := case")
    for state in states:
        lines.append(f"    state = {state_map[state]} : {output_map[model.nodes[state]]};")
    lines.append("  esac;")
    lines.append("")
    lines.append("ASSIGN")
    lines.append(f"  init(state) := {state_map[model.init]};")
    lines.append("")

    # Restrict current input values to labels that actually leave the current state.
    # This avoids false vacuity results when input is a CTL-visible VAR.
    # States with no outgoing DOT transition get NO_INPUT and remain deadlock states.
    lines.append("INVAR")
    lines.append("  case")
    for state in states:
        labels = sorted(enabled_by_state.get(state, set()))
        if labels:
            terms = [f"input = {input_map[label]}" for label in labels]
        else:
            terms = [f"input = {input_map[NO_INPUT]}"]
        lines.append(f"    state = {state_map[state]} : {disjunction(terms)};")
    lines.append("  esac;")
    lines.append("")

    # Exact DOT transition relation. No sink, no default self-loop, no missing edge.
    lines.append("TRANS")
    lines.append("  case")
    for src, label, dst in model.edges:
        lines.append(
            f"    state = {state_map[src]} & input = {input_map[label]} : next(state) = {state_map[dst]};"
        )
    lines.append("    TRUE : FALSE;")
    lines.append("  esac;")
    lines.append("")

    for input_level, attack_input, normal_input in expected_inputs(model):
        for pid, (kind, src_output, dst_outputs) in PROPS.items():
            input_label = attack_input if kind == "Attack" else normal_input
            beta = disjunction([f"output = {output_map[o]}" for o in dst_outputs])
            alpha = f"input = {input_map[input_label]} & output = {output_map[src_output]}"
            lines.append(f"-- {input_level} {pid} AG")
            lines.append(f"SPEC AG (({alpha}) -> AX ({beta}))")
            lines.append(f"-- {input_level} {pid} EF-vacuity")
            lines.append(f"SPEC EF ({alpha})")
    lines.extend([
        "",
        "-- MAPPINGS",
        "-- state_map: " + json.dumps(state_map, sort_keys=True),
        "-- input_map: " + json.dumps(input_map, sort_keys=True),
        "-- output_map: " + json.dumps(output_map, sort_keys=True),
    ])

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Convert IDS DOT Moore/PTA files to NuSMV CTL models without sink states or LTL specs."
    )
    parser.add_argument("dot_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("ids_results"))
    parser.add_argument("--run-nusmv", action="store_true", help="Run nusmv on generated files if it is installed.")
    args = parser.parse_args()

    if not args.dot_dir.exists() or not args.dot_dir.is_dir():
        raise SystemExit(f"DOT folder does not exist or is not a directory: {args.dot_dir}")

    smv_dir = args.out / "smv"
    smv_dir.mkdir(parents=True, exist_ok=True)

    dot_files = sorted(p for p in args.dot_dir.glob("*.dot") if not p.name.startswith("._"))
    if not dot_files:
        raise SystemExit(f"No .dot files found in: {args.dot_dir}")

    models = [parse_dot(p) for p in dot_files]
    rows = []
    for model in models:
        (smv_dir / (model.path.stem + ".smv")).write_text(generate_smv(model), encoding="utf-8")
        rows.extend(evaluate(model))

    fields = [
        "model_type", "dot_filename", "learning_set", "configuration", "input_level_or_top2_pair",
        "property_id", "input_label", "AG_result", "EF_antecedent_result", "final_symbol",
        "antecedent_edges_count", "violation_count", "violation_examples",
    ]
    with (args.out / "raw_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    commands = ["#!/usr/bin/env bash", "set -euo pipefail", 'cd "$(dirname "$0")"']
    for model in models:
        commands.append(f'nusmv "smv/{model.path.stem}.smv"')
    cmd_path = args.out / "nusmv_commands.sh"
    cmd_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
    cmd_path.chmod(0o755)

    if args.run_nusmv:
        exe = shutil.which("nusmv") or shutil.which("NuSMV")
        if not exe:
            raise SystemExit("NuSMV was requested but no nusmv/NuSMV executable was found.")
        logs = args.out / "nusmv_logs"
        logs.mkdir(exist_ok=True)
        for model in models:
            smv = smv_dir / (model.path.stem + ".smv")
            result = subprocess.run([exe, str(smv)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            (logs / (model.path.stem + ".out")).write_text(result.stdout, encoding="utf-8")


if __name__ == "__main__":
    main()

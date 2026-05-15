#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict, deque
import argparse
import csv
import json
import re
import shutil
import subprocess


NODE_RE = re.compile(
    r'^\s*([A-Za-z_][A-Za-z0-9_\-]*)\s*\[.*label\s*=\s*"([^"]*)".*\]\s*;?\s*$'
)
EDGE_RE = re.compile(
    r'^\s*([A-Za-z_][A-Za-z0-9_\-]*)\s*->\s*([A-Za-z_][A-Za-z0-9_\-]*)\s*\[.*label\s*=\s*"([^"]*)".*\]\s*;?\s*$'
)

IDS_OUTPUTS = ["Safe", "Warning", "Alert", "TWarning", "TAlert", "None"]
NO_INPUT = "NO_INPUT"

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


@dataclass(frozen=True)
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
    name = name.strip()
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not s:
        raise ValueError("Empty identifier after sanitization.")
    if not re.match(r"[A-Za-z_]", s):
        s = "_" + s
    reserved = {
        "TRUE", "FALSE", "MODULE", "VAR", "IVAR", "DEFINE", "ASSIGN",
        "TRANS", "INVAR", "SPEC", "case", "esac", "init", "next"
    }
    if s in reserved:
        s = s + "_id"
    return s


def sort_state(s: str):
    m = re.match(r"([A-Za-z]+)(\d+)$", s)
    return (m.group(1), int(m.group(2))) if m else (s, 0)


def parse_meta(filename: str):
    lower = filename.lower()
    model_type = "Moore" if lower.startswith("moore") else "PTA"
    dataset = "DDoS" if "ddos" in lower else "DoS5"
    if "top" in lower:
        config = "Top-2"
    elif "1st" in lower:
        config = "1st"
    elif "2nd" in lower:
        config = "2nd"
    else:
        config = "UNKNOWN"
    return model_type, dataset, config


def parse_dot(path: Path) -> Model:
    nodes: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    init: str | None = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("digraph") or line in {"{", "}"}:
            continue

        edge = EDGE_RE.match(line)
        if edge:
            src, dst, label = edge.groups()
            label = label.strip()
            if src.startswith("__start"):
                if init is not None and init != dst:
                    raise ValueError(f"{path.name}: multiple initial states: {init}, {dst}")
                init = dst
                continue
            if label == "":
                raise ValueError(f"{path.name}: empty label on ordinary edge {src}->{dst}")
            edges.append((src, label, dst))
            continue

        node = NODE_RE.match(line)
        if node:
            node_id, label = node.groups()
            if node_id.startswith("__start"):
                continue
            output = label.split("|", 1)[1].strip() if "|" in label else label.strip()
            nodes[node_id] = output

    if init is None:
        raise ValueError(f"{path.name}: missing __start initial edge")
    if init not in nodes:
        raise ValueError(f"{path.name}: initial state {init} has no node label")

    for src, _, dst in edges:
        if src not in nodes:
            raise ValueError(f"{path.name}: source state {src} has no node label")
        if dst not in nodes:
            raise ValueError(f"{path.name}: destination state {dst} has no node label")

    model_type, dataset, config = parse_meta(path.name)
    return Model(path, path.name, model_type, dataset, config, nodes, edges, init)


def expected_inputs(model: Model):
    if model.config == "Top-2":
        return [(f"({u},{f})", f"D_{u}_{f}", f"N_{u}_{f}") for u, f in TOP2]
    return [(name, f"D{letter}", f"N{letter}") for name, letter in LEVELS]


def reachable_states(model: Model):
    adj = defaultdict(list)
    for src, _, dst in model.edges:
        adj[src].append(dst)
    seen = {model.init}
    queue = deque([model.init])
    while queue:
        cur = queue.popleft()
        for dst in adj.get(cur, []):
            if dst not in seen:
                seen.add(dst)
                queue.append(dst)
    return seen


def finite_check(model: Model):
    trans = defaultdict(list)
    for src, label, dst in model.edges:
        trans[(src, label)].append(dst)

    reachable = reachable_states(model)
    rows = []

    for input_level, attack_input, normal_input in expected_inputs(model):
        for pid, (kind, src_output, dst_outputs) in PROPS.items():
            input_label = attack_input if kind == "Attack" else normal_input
            antecedent_edges = []
            violations = []

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
                "AG_expected": "TRUE" if ag else "FALSE",
                "EF_antecedent_expected": "TRUE" if ef else "FALSE",
                "final_symbol_expected": symbol,
                "antecedent_edges_count": len(antecedent_edges),
                "violation_count": len(violations),
                "violation_examples": "; ".join(
                    f"{s} --{i}--> {d}({o})" for s, i, d, o in violations[:10]
                ),
            })

    return rows


def make_output_constants(outputs: list[str]):
    return {out: f"OUT_{safe_name(out)}" for out in outputs}


def generate_smv(model: Model):
    states = sorted(model.nodes, key=sort_state)

    outgoing_by_state: dict[str, set[str]] = {s: set() for s in states}
    for src, label, _ in model.edges:
        outgoing_by_state[src].add(label)

    real_inputs = sorted({label for _, label, _ in model.edges})
    property_inputs = set()
    for _, attack_input, normal_input in expected_inputs(model):
        property_inputs.add(attack_input)
        property_inputs.add(normal_input)

    inputs = sorted(set(real_inputs) | property_inputs | {NO_INPUT})
    outputs = sorted(set(IDS_OUTPUTS) | set(model.nodes.values()))

    state_map = {s: safe_name(s) for s in states}
    input_map = {i: safe_name(i) for i in inputs}
    output_const = make_output_constants(outputs)

    lines = []
    lines.append("MODULE main")
    lines.append("")
    lines.append("VAR")
    lines.append("  state : {" + ", ".join(state_map[s] for s in states) + "};")
    lines.append("  input : {" + ", ".join(input_map[i] for i in inputs) + "};")
    lines.append("")
    lines.append("DEFINE")
    for idx, out in enumerate(outputs):
        lines.append(f"  {output_const[out]} := {idx};")
    lines.append("")
    lines.append("  output := case")
    for state in states:
        lines.append(f"    state = {state_map[state]} : {output_const[model.nodes[state]]};")
    lines.append("  esac;")
    lines.append("")
    lines.append("ASSIGN")
    lines.append(f"  init(state) := {state_map[model.init]};")
    lines.append("")
    lines.append("TRANS")
    lines.append("  case")

    # Real observed PTA transitions only.
    for src, label, dst in model.edges:
        lines.append(
            f"    state = {state_map[src]} & input = {input_map[label]} : "
            f"next(state) = {state_map[dst]};"
        )

    # Terminal stutter completion only. No sink state is introduced.
    leaves = [s for s in states if len(outgoing_by_state[s]) == 0]
    for leaf in leaves:
        lines.append(
            f"    state = {state_map[leaf]} & input = {input_map[NO_INPUT]} : "
            f"next(state) = {state_map[leaf]};"
        )

    lines.append("    TRUE : FALSE;")
    lines.append("  esac;")
    lines.append("")

    # Restrict input at each state. Non-leaf states can use only observed inputs
    # from that state. Leaf states can use only NO_INPUT.
    lines.append("INVAR")
    inv_parts = []
    for state in states:
        allowed = outgoing_by_state[state]
        if not allowed:
            allowed = {NO_INPUT}
        input_guard = " | ".join(f"input = {input_map[i]}" for i in sorted(allowed))
        inv_parts.append(f"(state = {state_map[state]} -> ({input_guard}))")
    lines.append("  " + " &\n  ".join(inv_parts))
    lines.append("")

    # CTL properties only. No LTLSPEC.
    for input_level, attack_input, normal_input in expected_inputs(model):
        for pid, (kind, src_output, dst_outputs) in PROPS.items():
            input_label = attack_input if kind == "Attack" else normal_input
            alpha = f"input = {input_map[input_label]} & output = {output_const[src_output]}"
            beta = " | ".join(f"output = {output_const[o]}" for o in dst_outputs)

            lines.append(f"-- {input_level} {pid} AG")
            lines.append(f"SPEC AG (({alpha}) -> AX ({beta}))")
            lines.append(f"-- {input_level} {pid} EF-vacuity")
            lines.append(f"SPEC EF ({alpha})")
            lines.append("")

    lines.append("-- MAPPINGS")
    lines.append("-- state_map: " + json.dumps(state_map, sort_keys=True))
    lines.append("-- input_map: " + json.dumps(input_map, sort_keys=True))
    lines.append("-- output_constants: " + json.dumps(output_const, sort_keys=True))
    lines.append("-- completion: leaf states have a NO_INPUT self-loop only; no sink state is added")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate NuSMV CTL models for finite PTA DOT files with terminal stutter completion only."
    )
    parser.add_argument("dot_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("pta_nusmv_stutter_results"))
    parser.add_argument(
        "--pta-only",
        action="store_true",
        default=True,
        help="Process only pta_*.dot files. This is the default.",
    )
    parser.add_argument("--include-moore", action="store_true", help="Also process Moore DOT files.")
    parser.add_argument("--run-nusmv", action="store_true")
    args = parser.parse_args()

    smv_dir = args.out / "smv"
    log_dir = args.out / "nusmv_logs_txt"
    smv_dir.mkdir(parents=True, exist_ok=True)

    dot_files = sorted(p for p in args.dot_dir.glob("*.dot") if not p.name.startswith("._"))
    if not args.include_moore:
        dot_files = [p for p in dot_files if p.name.lower().startswith("pta")]

    models = [parse_dot(p) for p in dot_files]

    rows = []
    for model in models:
        (smv_dir / f"{model.path.stem}.smv").write_text(generate_smv(model), encoding="utf-8")
        rows.extend(finite_check(model))

    fields = [
        "model_type", "dot_filename", "learning_set", "configuration",
        "input_level_or_top2_pair", "property_id", "input_label",
        "AG_expected", "EF_antecedent_expected", "final_symbol_expected",
        "antecedent_edges_count", "violation_count", "violation_examples"
    ]
    with (args.out / "expected_finite_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    commands = ["#!/usr/bin/env bash", "set -euo pipefail", 'cd "$(dirname "$0")"', "mkdir -p nusmv_logs_txt"]
    for model in models:
        stem = model.path.stem
        commands.append(f'nusmv "smv/{stem}.smv" > "nusmv_logs_txt/{stem}.txt" 2>&1')
    cmd_path = args.out / "run_all_nusmv.sh"
    cmd_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
    cmd_path.chmod(0o755)

    if args.run_nusmv:
        exe = shutil.which("nusmv") or shutil.which("NuSMV")
        if exe is None:
            raise SystemExit("NuSMV executable was not found.")
        log_dir.mkdir(exist_ok=True)
        for model in models:
            smv_path = smv_dir / f"{model.path.stem}.smv"
            result = subprocess.run(
                [exe, str(smv_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            (log_dir / f"{model.path.stem}.txt").write_text(result.stdout, encoding="utf-8")

    print(f"Generated {len(models)} SMV files in: {smv_dir}")
    print(f"Expected finite-transition results: {args.out / 'expected_finite_results.csv'}")
    print(f"Run script: {cmd_path}")


if __name__ == "__main__":
    main()

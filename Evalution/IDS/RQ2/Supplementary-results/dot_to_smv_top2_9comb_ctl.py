#!/usr/bin/env python3
"""
Convert Moore or PTA DOT files to NuSMV SMV files.

The generated SMV file has:
  - no sink state
  - no LTL properties
  - CTL properties written with NuSMV SPEC
  - EF antecedent checks for vacuity
  - all nine (F,U) table combinations:
      (LF,LU), (MF,LU), (HF,LU),
      (LF,MU), (MF,MU), (HF,MU),
      (LF,HU), (MF,HU), (HF,HU)

DOT edge labels are expected in this form:
  D_LU_LF, N_MU_MF, D_HU_HF, ...

Table column (MF,MU) maps to:
  Attack input: D_MU_MF
  Normal input: N_MU_MF
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Table order: (F, U)
COMBINATIONS: List[Tuple[str, str]] = [
    ("LF", "LU"), ("MF", "LU"), ("HF", "LU"),
    ("LF", "MU"), ("MF", "MU"), ("HF", "MU"),
    ("LF", "HU"), ("MF", "HU"), ("HF", "HU"),
]

# NuSMV-safe output constants.
# Add more here only if your DOT files use new output labels.
OUTPUT_VALUES = ["Alert", "None", "Safe", "TAlert", "TWarning", "Warning"]
OUTPUT_CODE = {name: i for i, name in enumerate(OUTPUT_VALUES)}


NODE_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[.*?label\s*=\s*"([^"]*)"', re.DOTALL)
EDGE_RE = re.compile(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)\s*'
    r'(?:\[.*?label\s*=\s*"([^"]*)".*?\])?\s*;',
    re.DOTALL,
)


def smv_id(raw: str) -> str:
    """Return a NuSMV-safe identifier."""
    s = re.sub(r"\W+", "_", raw.strip())
    s = s.strip("_") or "id"
    if re.match(r"^\d", s):
        s = "s_" + s
    return s


def parse_dot(dot_path: Path):
    """Read nodes, outputs, edges, and init state from a DOT file."""
    text = dot_path.read_text(encoding="utf-8")

    raw_to_smv: Dict[str, str] = {}
    output_by_state: Dict[str, str] = {}
    ordered_states: List[str] = []
    raw_edges: List[Tuple[str, str, str]] = []
    init_raw = None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue

        m_edge = EDGE_RE.match(line)
        if m_edge:
            src_raw, dst_raw, label = m_edge.groups()
            label = (label or "").strip()
            if src_raw.startswith("__start"):
                init_raw = dst_raw
                continue
            if label == "":
                continue
            raw_edges.append((src_raw, dst_raw, smv_id(label)))
            continue

        m_node = NODE_RE.match(line)
        if m_node:
            node_raw, label = m_node.groups()
            if node_raw.startswith("__start"):
                continue
            state = smv_id(node_raw)
            raw_to_smv[node_raw] = state
            ordered_states.append(state)

            # Expected node label: q0|Safe or s0|Warning
            if "|" in label:
                out = label.split("|")[-1].strip()
            else:
                out = label.strip()
            out = smv_id(out) if out else "None"
            output_by_state[state] = out

    # Include states that appear only in edges.
    for src_raw, dst_raw, _ in raw_edges:
        for raw in (src_raw, dst_raw):
            if raw not in raw_to_smv:
                state = smv_id(raw)
                raw_to_smv[raw] = state
                ordered_states.append(state)
                output_by_state[state] = "None"

    if not ordered_states:
        raise ValueError(f"No states found in {dot_path}")

    init_state = raw_to_smv.get(init_raw, ordered_states[0])

    # Group next states by (source state, input label).
    transitions: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    observed_inputs: Set[str] = set()
    outgoing_by_state: Dict[str, Set[str]] = defaultdict(set)

    for src_raw, dst_raw, label in raw_edges:
        src = raw_to_smv[src_raw]
        dst = raw_to_smv[dst_raw]
        transitions[(src, label)].add(dst)
        observed_inputs.add(label)
        outgoing_by_state[src].add(label)

    # Add NO_INPUT self loop for terminal states. This keeps the model total without a sink.
    for state in ordered_states:
        if not outgoing_by_state[state]:
            transitions[(state, "NO_INPUT")].add(state)
            outgoing_by_state[state].add("NO_INPUT")
            observed_inputs.add("NO_INPUT")

    return ordered_states, output_by_state, transitions, outgoing_by_state, observed_inputs, init_state


def all_table_inputs() -> Set[str]:
    labels = {"NO_INPUT"}
    for f_val, u_val in COMBINATIONS:
        labels.add(f"D_{u_val}_{f_val}")
        labels.add(f"N_{u_val}_{f_val}")
    return labels


def or_join(parts: List[str]) -> str:
    if not parts:
        return "FALSE"
    if len(parts) == 1:
        return parts[0]
    return "(" + " | ".join(parts) + ")"


def set_or_single(states: Set[str]) -> str:
    items = sorted(states, key=lambda x: (len(x), x))
    if len(items) == 1:
        return f"next(state) = {items[0]}"
    return "next(state) in {" + ", ".join(items) + "}"


def spec_pair(name: str, input_label: str, src_output: str, dst_expr: str) -> str:
    antecedent = f"input = {input_label} & output = {src_output}"
    return (
        f"-- {name}\n"
        f"SPEC AG (({antecedent}) -> AX ({dst_expr}))\n"
        f"SPEC EF ({antecedent})\n"
    )


def build_specs() -> str:
    chunks: List[str] = []
    chunks.append("-- ============================================================")
    chunks.append("-- CTL properties from the table, plus EF antecedent checks")
    chunks.append("-- NuSMV uses SPEC for CTL formulas")
    chunks.append("-- Interpretation:")
    chunks.append("--   AG false                    -> fail")
    chunks.append("--   AG true and EF false        -> vacuous")
    chunks.append("--   AG true and EF true         -> pass")
    chunks.append("-- ============================================================\n")

    for f_val, u_val in COMBINATIONS:
        col = f"({f_val},{u_val})"
        attack = f"D_{u_val}_{f_val}"
        normal = f"N_{u_val}_{f_val}"

        chunks.append(f"-- ===== Table column {col} =====")
        chunks.append(spec_pair(f"R1_1 Attack and S, {col}", attack, "Safe", "output = Warning | output = TWarning"))
        chunks.append(spec_pair(f"R1_2 Attack and W, {col}", attack, "Warning", "output = Alert | output = TAlert"))
        chunks.append(spec_pair(f"R1_3 Attack and A, {col}", attack, "Alert", "output = Alert | output = TAlert"))
        chunks.append(spec_pair(f"R2_1 Normal and S, {col}", normal, "Safe", "output = Safe"))
        chunks.append(spec_pair(f"R2_2 Normal and W, {col}", normal, "Warning", "output = Safe"))
        chunks.append(spec_pair(f"R2_3 Normal and A, {col}", normal, "Alert", "output = Warning | output = TWarning"))

    return "\n".join(chunks)


def write_smv(dot_path: Path, out_path: Path) -> None:
    states, output_by_state, transitions, outgoing_by_state, observed_inputs, init_state = parse_dot(dot_path)

    # Include all table input labels so all requested SPEC formulas are valid.
    input_values = sorted(observed_inputs | all_table_inputs())

    lines: List[str] = []
    lines.append("MODULE main\n")

    lines.append("VAR")
    lines.append("  state : {" + ", ".join(states) + "};")
    lines.append("  input : {" + ", ".join(input_values) + "};\n")

    lines.append("DEFINE")
    for name in OUTPUT_VALUES:
        lines.append(f"  {name} := {OUTPUT_CODE[name]};")
    lines.append("")
    lines.append("  output := case")
    for state in states:
        out = output_by_state.get(state, "None")
        if out not in OUTPUT_CODE:
            raise ValueError(
                f"Unsupported output label '{out}' in {dot_path}. "
                f"Add it to OUTPUT_VALUES in the script."
            )
        lines.append(f"    state = {state} : {out};")
    lines.append("  esac;\n")

    lines.append("ASSIGN")
    lines.append(f"  init(state) := {init_state};\n")

    lines.append("INVAR")
    lines.append("  case")
    for state in states:
        allowed = sorted(outgoing_by_state.get(state, {"NO_INPUT"}))
        cond = or_join([f"input = {x}" for x in allowed])
        lines.append(f"    state = {state} : {cond};")
    lines.append("  esac;\n")

    lines.append("TRANS")
    lines.append("  case")
    for (src, label), dsts in sorted(transitions.items(), key=lambda item: (item[0][0], item[0][1])):
        lines.append(f"    state = {src} & input = {label} : {set_or_single(dsts)};")
    lines.append("    TRUE : TRUE;")
    lines.append("  esac;\n")

    lines.append(build_specs())
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Moore/PTA DOT files to NuSMV SMV files with Top-2 nine-combination CTL specs."
    )
    parser.add_argument("dot_files", nargs="+", help="Input DOT file(s)")
    parser.add_argument(
        "-o", "--out-dir",
        default=None,
        help="Output directory. Default: same directory as each DOT file.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve() if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for dot_name in args.dot_files:
        dot_path = Path(dot_name).resolve()
        if not dot_path.exists():
            raise FileNotFoundError(dot_path)

        target_dir = out_dir if out_dir else dot_path.parent
        out_path = target_dir / (dot_path.stem + "_ctl_9comb.smv")
        write_smv(dot_path, out_path)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

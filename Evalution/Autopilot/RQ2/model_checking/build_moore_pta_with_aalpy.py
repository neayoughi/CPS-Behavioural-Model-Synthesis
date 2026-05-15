#!/usr/bin/env python3
"""
Build the initial PTA (no merges) as a Moore machine using AALpy.

Input format (per .txt file):
  A Python list literal with elements shaped like:
    ((symbol_1, ..., symbol_n), label)
  Example:
    [(('NL',), 'Safe'), (('NL','NL'), 'Safe')]

Usage examples:
  python build_moore_pta_with_aalpy.py --folder "/path/to/traces" --pattern "Trace_*.txt" --out_dir out
  python build_moore_pta_with_aalpy.py --input  "/path/to/traces/Trace_1st.txt" --out_dir out

Outputs (in --out_dir):
  - pta_moore.dot
  - pta_summary.txt
"""

from __future__ import annotations

import argparse
import ast
import os
from typing import Dict, List, Optional, Tuple

from aalpy.automata import MooreMachine, MooreState

import shutil
import subprocess

def render_dot_to_pdf(dot_path: str, pdf_path: str) -> None:
    if shutil.which("dot") is None:
        raise RuntimeError("Graphviz 'dot' not found. Install graphviz and retry.")
    subprocess.run(["dot", "-Tpdf", dot_path, "-o", pdf_path], check=True)

def _read_list_literal(path: str):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read().strip()
    if not txt:
        return []
    return ast.literal_eval(txt)


def load_samples_from_file(path: str) -> List[Tuple[Tuple[str, ...], str]]:
    """
    Returns: list of (sequence, output_label)
    sequence is a tuple of symbols (strings).
    """
    data = _read_list_literal(path)
    samples: List[Tuple[Tuple[str, ...], str]] = []

    for item in data:
        if not (isinstance(item, tuple) and len(item) == 2):
            raise ValueError(f"Bad sample record in {path}: {item!r}")

        seq, out = item

        if isinstance(seq, list):
            seq = tuple(seq)
        if not isinstance(seq, tuple):
            raise TypeError(f"Unexpected sequence type in {path}: {type(seq)}")

        seq = tuple(str(x) for x in seq)
        out = str(out)
        samples.append((seq, out))

    return samples


def load_samples(folder: str, pattern: str) -> Tuple[List[Tuple[Tuple[str, ...], str]], List[str]]:
    """
    Loads samples from all matching files in a folder.
    Each file is a Python list literal of samples.
    """
    import glob

    folder = os.path.abspath(folder)
    files = sorted(glob.glob(os.path.join(folder, pattern)))
    if not files:
        raise FileNotFoundError(f"No files match pattern {pattern!r} in folder {folder!r}")

    all_samples: List[Tuple[Tuple[str, ...], str]] = []
    for fp in files:
        all_samples.extend(load_samples_from_file(fp))

    return all_samples, files


def build_moore_pta(samples: List[Tuple[Tuple[str, ...], str]]) -> MooreMachine:
    """
    PTA as a Moore machine:
      - one state per prefix
      - output label stored on the prefix state
      - transitions follow the prefix tree
    """
    root = MooreState("q0", output=None)
    states_by_prefix: Dict[Tuple[str, ...], MooreState] = {(): root}

    def get_state(pref: Tuple[str, ...]) -> MooreState:
        st = states_by_prefix.get(pref)
        if st is None:
            st = MooreState(f"q{len(states_by_prefix)}", output=None)
            states_by_prefix[pref] = st
        return st

    for seq, out in samples:
        pref: Tuple[str, ...] = ()
        cur = get_state(pref)

        for a in seq:
            next_pref = pref + (a,)
            nxt = get_state(next_pref)

            if getattr(cur, "transitions", None) is None:
                cur.transitions = {}
            cur.transitions[a] = nxt

            pref = next_pref
            cur = nxt

        if cur.output is None:
            cur.output = out
        elif cur.output != out:
            raise ValueError(
                f"Conflicting outputs for prefix {seq}: {cur.output!r} vs {out!r}"
            )

    return MooreMachine(root, list(states_by_prefix.values()))


def count_states_edges(moore: MooreMachine) -> Tuple[int, int]:
    """
    Counts reachable states and edges.
    """
    from collections import deque

    seen = set()
    q = deque([moore.initial_state])
    seen.add(moore.initial_state)

    edges = 0
    while q:
        s = q.popleft()
        trans = getattr(s, "transitions", {}) or {}
        edges += len(trans)
        for _, t in trans.items():
            if t not in seen:
                seen.add(t)
                q.append(t)

    return len(seen), edges


def save_dot_compat(automaton, out_dot_path: str) -> None:
    """
    AALpy changed the save() signature across versions.
    This helper tries the common variants and falls back to aalpy.utils.
    out_dot_path must end with '.dot'.
    """
    out_base = out_dot_path[:-4] if out_dot_path.endswith(".dot") else out_dot_path

    # Variant A: save(path=..., file_type=...)
    try:
        automaton.save(path=out_base, file_type="dot")
        return
    except TypeError:
        pass

    # Variant B: save(file_path, file_type)
    try:
        automaton.save(out_base, "dot")
        return
    except TypeError:
        pass

    # Variant C: utils function
    try:
        from aalpy.utils import save_automaton_to_file
        save_automaton_to_file(automaton, out_base, file_type="dot")
        return
    except Exception as e:
        raise RuntimeError(f"Could not save DOT via AALpy. Underlying error: {e}") from e


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=str, default=None, help="Folder that contains trace .txt files")
    ap.add_argument("--pattern", type=str, default="*.txt", help="Glob pattern inside folder, e.g., 'Trace_*.txt'")
    ap.add_argument("--input", type=str, default=None, help="Single trace file path (overrides --folder/--pattern)")
    ap.add_argument("--out_dir", type=str, default=".", help="Output directory")
    args = ap.parse_args()

    if args.input:
        in_path = os.path.abspath(os.path.expanduser(args.input))
        if not os.path.isfile(in_path):
            raise FileNotFoundError(
                f"Input file not found: {in_path}\n"
                f"Tip: use an absolute path, e.g. '/Users/<name>/.../Trace_1st.txt'"
            )
        samples = load_samples_from_file(in_path)
        src_files = [in_path]
    else:
        if not args.folder:
            raise SystemExit("Provide --input or provide --folder.")
        samples, src_files = load_samples(os.path.expanduser(args.folder), args.pattern)

    moore_pta = build_moore_pta(samples)
    n_states, n_edges = count_states_edges(moore_pta)

    out_dir = os.path.abspath(os.path.expanduser(args.out_dir))
    os.makedirs(out_dir, exist_ok=True)

    out_dot = os.path.join(out_dir, "pta_moore.dot")
    save_dot_compat(moore_pta, out_dot)

    summary_lines = [
        f"source_files: {'; '.join(src_files)}",
        f"num_samples: {len(samples)}",
        f"pta_states_reachable: {n_states}",
        f"pta_edges_reachable: {n_edges}",
        f"dot_file: {out_dot}",
    ]
    summary_text = "\n".join(summary_lines) + "\n"
    with open(os.path.join(out_dir, "pta_summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary_text)
    print(summary_text)

    pdf_path = os.path.join(out_dir, "pta_moore.pdf")
    render_dot_to_pdf(out_dot, pdf_path)


if __name__ == "__main__":
    main()

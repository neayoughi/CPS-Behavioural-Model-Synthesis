#!/usr/bin/env python3
"""
Append Attack-only CTL checks for atomic TW/TA next-state behavior.

Generated AG checks:
  TW -> AX(TW)
  TW -> AX(W)
  TW -> AX(TA)
  TW -> AX(A)
  TA -> AX(TW)
  TA -> AX(W)
  TA -> AX(TA)
  TA -> AX(A)

For each AG check, an EF antecedent reachability check is added.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Iterable

START_MARKER = "-- === BEGIN AUTO-GENERATED ATTACK TW/TA ATOMIC CTL SPECS ==="
END_MARKER = "-- === END AUTO-GENERATED ATTACK TW/TA ATOMIC CTL SPECS ==="

# NuSMV output symbols used in your SMV files.
OUTPUT = {
    "TW": "TWarning",
    "W": "Warning",
    "TA": "TAlert",
    "A": "Alert",
}

# Current output, target output, short label.
PROPERTIES = [
    ("TW", "TW", "TW_AX_TW"),
    ("TW", "W",  "TW_AX_W"),
    ("TW", "TA", "TW_AX_TA"),
    ("TW", "A",  "TW_AX_A"),
    ("TA", "TW", "TA_AX_TW"),
    ("TA", "W",  "TA_AX_W"),
    ("TA", "TA", "TA_AX_TA"),
    ("TA", "A",  "TA_AX_A"),
]

STANDARD_ATTACK_ORDER = ["DL", "DM", "DH"]
U_ORDER = ["LU", "MU", "HU"]
F_ORDER = ["LF", "MF", "HF"]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def strip_old_block(text: str) -> str:
    """Remove a prior block made by this script, if it exists."""
    pattern = re.compile(
        rf"\n*{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}\n*",
        flags=re.DOTALL,
    )
    return pattern.sub("\n", text).rstrip()


def parse_input_symbols(text: str) -> list[str]:
    """Extract symbols from the NuSMV declaration: input : {...};"""
    match = re.search(r"\binput\s*:\s*\{([^}]*)\}\s*;", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Could not find an input enum declaration such as: input : {...};")

    return [token.strip() for token in match.group(1).replace("\n", " ").split(",") if token.strip()]


def attack_sort_key(symbol: str) -> tuple[int, int, int, str]:
    """Sort DL/DM/DH first, then Top-2 labels in LU/MU/HU x LF/MF/HF order."""
    if symbol in STANDARD_ATTACK_ORDER:
        return (0, STANDARD_ATTACK_ORDER.index(symbol), 0, symbol)

    # Expected Top-2 form: D_LU_LF, D_MU_MF, etc.
    match = re.fullmatch(r"D_(LU|MU|HU)_(LF|MF|HF)", symbol)
    if match:
        u_level, f_level = match.groups()
        return (1, U_ORDER.index(u_level), F_ORDER.index(f_level), symbol)

    return (2, 0, 0, symbol)


def attack_inputs_from_text(text: str) -> list[str]:
    symbols = parse_input_symbols(text)
    attack_inputs = [s for s in symbols if s != "NO_INPUT" and s.startswith("D")]
    return sorted(attack_inputs, key=attack_sort_key)


def specs_for_attack_inputs(attack_inputs: Iterable[str]) -> str:
    lines: list[str] = [
        "",
        START_MARKER,
        "-- Attack-only CTL properties for atomic TW/TA next-state checks.",
        "-- Symbol map: TW=TWarning, TA=TAlert, W=Warning, A=Alert.",
        "-- Result interpretation: AG true + EF true = Pass; AG true + EF false = v; AG false = Fail.",
    ]

    for input_symbol in attack_inputs:
        lines.append(f"\n-- ----- Attack input: {input_symbol} -----")
        for current_short, target_short, prop_name in PROPERTIES:
            current_output = OUTPUT[current_short]
            target_output = OUTPUT[target_short]
            spec_id = f"{input_symbol}_{prop_name}"

            lines.append(f"\n-- {spec_id}_AG: {current_short} -> AX({target_short})")
            lines.append(
                f"SPEC AG ((input = {input_symbol} & output = {current_output}) "
                f"-> AX (output = {target_output}))"
            )
            lines.append(f"-- {spec_id}_EF: antecedent reachability check")
            lines.append(f"SPEC EF (input = {input_symbol} & output = {current_output})")

    lines.extend(["", END_MARKER, ""])
    return "\n".join(lines)


def update_one_smv(src: Path, dst: Path) -> list[str]:
    text = read_text(src)
    attack_inputs = attack_inputs_from_text(text)
    if not attack_inputs:
        raise ValueError(f"No Attack input symbols found in {src}")

    updated = strip_old_block(text) + specs_for_attack_inputs(attack_inputs)
    write_text(dst, updated)
    return attack_inputs


def iter_smv_files(src_dir: Path) -> list[Path]:
    files = sorted(src_dir.glob("*.smv"))
    if not files:
        raise FileNotFoundError(f"No .smv files found in {src_dir}")
    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append Attack-only TW/TA atomic CTL specs to NuSMV files."
    )
    parser.add_argument("--src_dir", type=Path, default=Path("smv"), help="Folder with .smv files.")
    parser.add_argument(
        "--out_dir",
        type=Path,
        default=Path("smv_with_attack_tw_ta_atomic_specs"),
        help="Folder for updated .smv files.",
    )
    parser.add_argument(
        "--in_place",
        action="store_true",
        help="Rewrite source .smv files instead of writing to --out_dir.",
    )
    args = parser.parse_args()

    src_dir = args.src_dir
    smv_files = iter_smv_files(src_dir)

    if args.in_place:
        for src in smv_files:
            inputs = update_one_smv(src, src)
            print(f"Updated {src}: {', '.join(inputs)}")
    else:
        out_dir = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        for src in smv_files:
            dst = out_dir / src.name
            inputs = update_one_smv(src, dst)
            print(f"Wrote {dst}: {', '.join(inputs)}")
        shutil.copy2(Path(__file__), out_dir / Path(__file__).name)


if __name__ == "__main__":
    main()

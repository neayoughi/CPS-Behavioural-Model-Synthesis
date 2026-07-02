from pathlib import Path
import shutil

SRC_DIR = Path('smv')
OUT_DIR = Path('smv_with_tw_ta_specs_all_levels')

LEVELS_STANDARD = {
    'Low':  {'Attack': 'DL', 'Normal': 'NL'},
    'Med':  {'Attack': 'DM', 'Normal': 'NM'},
    'High': {'Attack': 'DH', 'Normal': 'NH'},
}

LEVELS_TOP2 = {
    'Low':  {'Attack': 'D_LU_LF', 'Normal': 'N_LU_LF'},
    'Med':  {'Attack': 'D_MU_MF', 'Normal': 'N_MU_MF'},
    'High': {'Attack': 'D_HU_HF', 'Normal': 'N_HU_HF'},
}

PROPERTIES = [
    ('QC1', 'AG(Attack & TW -> AX(TW | W))',
     'Attack', 'TWarning', '(output = TWarning | output = Warning)'),
    ('QC2', 'AG(Attack & TW -> AX(TA | A))',
     'Attack', 'TWarning', '(output = TAlert | output = Alert)'),
    ('QC3', 'AG(Attack & TA -> AX(TW | W))',
     'Attack', 'TAlert', '(output = TWarning | output = Warning)'),
    ('QC4', 'AG(Attack & TA -> AX(TA | A))',
     'Attack', 'TAlert', '(output = TAlert | output = Alert)'),
    ('QC5', 'AG(Normal & TW -> AX(TW | S))',
     'Normal', 'TWarning', '(output = TWarning | output = Safe)'),
    ('QC6', 'AG(Normal & TA -> AX(TA | W | TW))',
     'Normal', 'TAlert', '(output = TAlert | output = Warning | output = TWarning)'),
]

HEADER = """

-- ============================================================
-- Added CTL properties for TW/TA behavior table
-- Symbol map:
--   TW = TWarning, TA = TAlert, W = Warning, A = Alert, S = Safe
-- Result interpretation:
--   AG true and EF true  => Pass
--   AG true and EF false => Vacuous
--   AG false             => Fail
-- ============================================================
"""

def specs_for_file(path: Path) -> str:
    is_top2 = 'Top-2' in path.name or 'top2' in path.name.lower()
    levels = LEVELS_TOP2 if is_top2 else LEVELS_STANDARD
    lines = [HEADER]
    for level_name, symbols in levels.items():
        lines.append(f"\n-- ===== {level_name} level =====")
        for prop_id, informal, kind, current_output, next_expr in PROPERTIES:
            input_symbol = symbols[kind]
            lines.append(f"\n-- {prop_id}_{level_name}_AG: {informal}")
            lines.append(
                f"SPEC AG ((input = {input_symbol} & output = {current_output}) -> AX {next_expr})"
            )
            lines.append(f"-- {prop_id}_{level_name}_EF: antecedent reachability check")
            lines.append(f"SPEC EF (input = {input_symbol} & output = {current_output})")
    lines.append("")
    return "\n".join(lines)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for src in sorted(SRC_DIR.glob('*.smv')):
        dst = OUT_DIR / src.name
        text = src.read_text()
        dst.write_text(text.rstrip() + specs_for_file(src))
    shutil.copy2(Path(__file__), OUT_DIR / Path(__file__).name)
    print(f"Wrote updated files to {OUT_DIR}")

if __name__ == '__main__':
    main()

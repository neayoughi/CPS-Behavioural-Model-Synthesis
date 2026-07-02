from pathlib import Path
import re

SRC_DIR = Path('.')
OUT_DIR = Path('pta_with_tw_ta_specs_all_levels')

BEGIN = '-- BEGIN TW_TA_QC_CTL_SPECS_ALL_LEVELS'
END = '-- END TW_TA_QC_CTL_SPECS_ALL_LEVELS'

props = [
    ('QC1', 'AG(Attack & TW -> AX(TW | W))', 'attack', 'OUT_TWarning', ['OUT_TWarning', 'OUT_Warning']),
    ('QC2', 'AG(Attack & TW -> AX(TA | A))', 'attack', 'OUT_TWarning', ['OUT_TAlert', 'OUT_Alert']),
    ('QC3', 'AG(Attack & TA -> AX(TW | W))', 'attack', 'OUT_TAlert', ['OUT_TWarning', 'OUT_Warning']),
    ('QC4', 'AG(Attack & TA -> AX(TA | A))', 'attack', 'OUT_TAlert', ['OUT_TAlert', 'OUT_Alert']),
    ('QC5', 'AG(Normal & TW -> AX(TW | S))', 'normal', 'OUT_TWarning', ['OUT_TWarning', 'OUT_Safe']),
    ('QC6', 'AG(Normal & TA -> AX(TA | W | TW))', 'normal', 'OUT_TAlert', ['OUT_TAlert', 'OUT_Warning', 'OUT_TWarning']),
]

simple_levels = [
    ('Low', 'DL', 'NL'),
    ('Med', 'DM', 'NM'),
    ('High', 'DH', 'NH'),
]

top2_levels = [
    ('Low', 'D_LU_LF', 'N_LU_LF'),
    ('Med', 'D_MU_MF', 'N_MU_MF'),
    ('High', 'D_HU_HF', 'N_HU_HF'),
]

def strip_old_block(text: str) -> str:
    pattern = re.compile(r"\n?" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    return pattern.sub('\n', text).rstrip() + '\n'

def build_block(is_top2: bool) -> str:
    levels = top2_levels if is_top2 else simple_levels
    lines = ['', BEGIN]
    lines.append('-- Auto-added CTL checks for TW/TA behaviour at Low, Med, and High levels.')
    lines.append('-- Interpretation: AG=false -> Fail; AG=true and EF=false -> Vacuous; AG=true and EF=true -> Pass.')
    for level, attack_input, normal_input in levels:
        lines.append('')
        lines.append(f'-- ===== {level} level =====')
        for code, pretty, kind, antecedent_output, consequent_outputs in props:
            inp = attack_input if kind == 'attack' else normal_input
            consequent = ' | '.join(f'output = {out}' for out in consequent_outputs)
            lines.append(f'-- {code} {level}: {pretty}')
            lines.append(f'SPEC AG ((input = {inp} & output = {antecedent_output}) -> AX ({consequent}))')
            lines.append(f'SPEC EF (input = {inp} & output = {antecedent_output})')
    lines.append(END)
    lines.append('')
    return '\n'.join(lines)

def main():
    smv_files = sorted(p for p in SRC_DIR.glob('pta_*.smv') if p.is_file())
    if not smv_files:
        raise SystemExit('No pta_*.smv files found in the current folder.')
    OUT_DIR.mkdir(exist_ok=True)
    for path in smv_files:
        text = strip_old_block(path.read_text())
        is_top2 = 'top2' in path.name.lower() or 'top-2' in path.name.lower()
        (OUT_DIR / path.name).write_text(text + build_block(is_top2))
    print(f'Wrote {len(smv_files)} updated files to {OUT_DIR}')

if __name__ == '__main__':
    main()

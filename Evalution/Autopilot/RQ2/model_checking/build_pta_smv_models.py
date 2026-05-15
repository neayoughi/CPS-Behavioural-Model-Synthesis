#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from smv_model_checking_core import SMV_ROOT, build_model, parse_dot


PTA_ROOT = SMV_ROOT


@dataclass(frozen=True)
class PtaConfig:
    family: str
    case_key: str
    output_case: str
    dot_path: Path
    output_path: Path


def pta_config(family: str, case_key: str, output_case: str) -> PtaConfig:
    return PtaConfig(
        family=family,
        case_key=case_key,
        output_case=output_case,
        dot_path=PTA_ROOT / family / "PTA" / "pta_models" / "MELA" / output_case / "pta_moore.dot",
        output_path=PTA_ROOT / family / "PTA" / "generated_models" / output_case / f"pta_{output_case}_model.smv",
    )


CONFIGS = [
    pta_config("ascend", "pitchwheel_throttle", "pitchwheel_throttle"),
    pta_config("ascend", "pitchwheel", "pitchwheel"),
    pta_config("ascend", "throttle", "throttle"),
    pta_config("descend", "pitchwheel_throttle", "pitchwheel_throttle"),
    pta_config("descend", "pitchwheel", "pitchwheel"),
    pta_config("descend", "throttle", "throttle"),
]


def main() -> None:
    written: list[Path] = []
    for config in CONFIGS:
        machine = parse_dot(config.dot_path)
        config.output_path.parent.mkdir(parents=True, exist_ok=True)
        config.output_path.write_text(build_model(machine, config.case_key), encoding="utf-8")
        written.append(config.output_path)
        print(f"Wrote {config.output_path}")
    print(f"Completed PTA model build: {len(written)} models")


if __name__ == "__main__":
    main()

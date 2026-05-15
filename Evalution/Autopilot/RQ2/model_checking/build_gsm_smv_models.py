#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from smv_model_checking_core import DOT_CONFIGS, SMV_ROOT, build_model, model_output_path, parse_dot


MODEL_ROOT = SMV_ROOT


def main() -> None:
    written: list[Path] = []
    for config in DOT_CONFIGS:
        case_key = str(config["case_key"])
        machine = parse_dot(Path(config["dot_path"]))
        output_path = model_output_path(MODEL_ROOT, config, with_sink=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_model(machine, case_key), encoding="utf-8")
        written.append(output_path)
        print(f"Wrote {output_path}")

    print(f"Completed model build: {len(written)} models")


if __name__ == "__main__":
    main()

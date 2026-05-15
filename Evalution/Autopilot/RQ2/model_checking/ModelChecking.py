from __future__ import annotations

import subprocess
import sys
from pathlib import Path


learning_sets = ["ascend", "descend"]
configurations = ["pitchwheel", "throttle", "pitchwheel_throttle"]


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Results").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate project root from {start}")


project_root = find_project_root(Path(__file__))
code_root = project_root / "Code" / "Autopilot"


def project_path(relative_path: str) -> Path:
    return project_root / relative_path


def run_script(script_name: str) -> None:
    script_path = code_root / "model_checking" / script_name
    if not script_path.exists():
        raise SystemExit(f"Missing model-checking script: {script_path}")
    subprocess.run([sys.executable, str(script_path)], check=True, cwd=script_path.parent)


def main() -> None:
    run_script("build_gsm_smv_models.py")
    run_script("run_gsm_nusmv_checks.py")


if __name__ == "__main__":
    main()

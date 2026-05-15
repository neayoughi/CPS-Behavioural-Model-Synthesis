#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import logging
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Results").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate Autopilot project root from {start}")

PROJECT_ROOT = find_project_root(Path(__file__))
ROOT = PROJECT_ROOT
LEARNED_MODEL_ROOT = PROJECT_ROOT / "Results" / "LearnedModel" / "Autopilot"
ASCEND_TRAINING_ROOT = LEARNED_MODEL_ROOT / "MELA" / "ascend"
DESCEND_TRAINING_ROOT = LEARNED_MODEL_ROOT / "MELA" / "descend"
PTA_ROOT = PROJECT_ROOT / "Results" / "RQ2" / "Autopilot"
TRACE_COPY_ROOT = PTA_ROOT
PROVIDED_PTA_BUILDER = Path(__file__).resolve().parent / "build_moore_pta_with_aalpy.py"


@dataclass(frozen=True)
class ModelTraceSet:
    family: str
    case_key: str
    source_dot: Path
    source_traces: tuple[Path, ...]
    rel_model_dir: Path


def load_provided_pta_builder(builder_path: Path):
    builder_path = builder_path.resolve()
    if not builder_path.exists():
        raise FileNotFoundError(f"Provided PTA builder not found: {builder_path}")

    spec = importlib.util.spec_from_file_location("provided_build_pta_moore_aalpy", builder_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load PTA builder module from {builder_path}")

    module = importlib.util.module_from_spec(spec)
    old_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old_dont_write_bytecode

    required_functions = (
        "load_samples_from_file",
        "build_moore_pta",
        "count_states_edges",
        "save_dot_compat",
        "render_dot_to_pdf",
    )
    missing = [name for name in required_functions if not hasattr(module, name)]
    if missing:
        raise AttributeError(f"Provided PTA builder is missing required functions: {missing}")
    return module


def versioned_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_v{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find free versioned path for {path}")


def versioned_output_pair(output_dir: Path, trace_dir: Path) -> tuple[Path, Path]:
    if not output_dir.exists() and not trace_dir.exists():
        return output_dir, trace_dir

    for index in range(2, 1000):
        candidate_output = output_dir.with_name(f"{output_dir.name}_v{index}")
        candidate_trace = trace_dir.with_name(f"{trace_dir.name}_v{index}")
        if not candidate_output.exists() and not candidate_trace.exists():
            return candidate_output, candidate_trace
    raise RuntimeError(f"Could not find free versioned output folders for {output_dir}")


def configure_logging(pta_root: Path) -> Path:
    pta_root.mkdir(parents=True, exist_ok=True)
    log_path = versioned_path(pta_root / "logs" / "pta_build.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_path


def family_training_roots() -> dict[str, Path]:
    return {
        "ascend": ASCEND_TRAINING_ROOT,
        "descend": DESCEND_TRAINING_ROOT,
    }


def trace_family_root(source_dot: Path) -> Path:
    parts = source_dot.parts
    if "gsm_models" not in parts:
        return source_dot.parent
    gsm_index = parts.index("gsm_models")
    return Path(*parts[:gsm_index])


def model_provider(source_dot: Path) -> str | None:
    parts = source_dot.parts
    if "gsm_models" not in parts:
        return None
    gsm_index = parts.index("gsm_models")
    provider_index = gsm_index + 1
    if provider_index >= len(parts) - 1:
        return None
    return parts[provider_index]


def unique_existing(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    existing: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            existing.append(resolved)
    return existing


def find_source_traces(source_dot: Path, case_key: str) -> tuple[Path, ...]:
    family_root = trace_family_root(source_dot)
    provider = model_provider(source_dot)

    preferred: list[Path] = [
        source_dot.parent / f"{case_key}_trace_literal.txt",
    ]
    if provider is not None:
        preferred.append(family_root / "traces" / provider / f"{case_key}_full_history_trace.txt")
    preferred.append(family_root / "traces" / f"{case_key}_full_history_trace.txt")

    recursive = sorted(family_root.glob(f"**/{case_key}_trace_literal.txt"))
    recursive.extend(sorted(family_root.glob(f"**/{case_key}_full_history_trace.txt")))

    candidates = unique_existing([*preferred, *recursive])
    if not candidates:
        raise FileNotFoundError(f"No matching trace .txt found for {source_dot}")

    # The GSM builders store either a same-folder trace literal or a matching
    # full-history trace. If both exist, they are mirrored copies in this tree;
    # use the first preferred source so the PTA gets each trace set once.
    return (candidates[0],)


def discover_model_trace_sets(training_roots: dict[str, Path]) -> list[ModelTraceSet]:
    discovered: list[ModelTraceSet] = []
    for family, training_root in training_roots.items():
        training_root = training_root.resolve()
        if not training_root.exists():
            raise FileNotFoundError(f"Training root not found: {training_root}")

        for source_dot in sorted(training_root.glob("**/*_model.dot")):
            if not is_mela_model(source_dot):
                continue
            case_key = source_dot.name[: -len("_model.dot")]
            source_traces = find_source_traces(source_dot, case_key)
            output_case = case_key
            rel_model_dir = Path(family) / "PTA" / "pta_models" / "MELA" / output_case
            discovered.append(
                ModelTraceSet(
                    family=family,
                    case_key=case_key,
                    source_dot=source_dot.resolve(),
                    source_traces=source_traces,
                    rel_model_dir=rel_model_dir,
                )
            )
    return discovered


def is_mela_model(source_dot: Path) -> bool:
    parts = source_dot.parts
    return "MELA" in parts or model_provider(source_dot) == "mela"


def write_original_pta_summary(
    path: Path,
    source_files: list[str],
    sample_count: int,
    reachable_states: int,
    reachable_edges: int,
    dot_file: Path,
) -> None:
    lines = [
        f"source_files: {'; '.join(source_files)}",
        f"num_samples: {sample_count}",
        f"pta_states_reachable: {reachable_states}",
        f"pta_edges_reachable: {reachable_edges}",
        f"dot_file: {dot_file}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    fieldnames = [
        "family",
        "case_key",
        "model_trace_set",
        "source_dot",
        "source_trace_paths",
        "copied_trace_paths",
        "pta_output_dir",
        "pta_dot",
        "pta_pdf",
        "pta_summary_txt",
        "sample_count",
        "reachable_pta_states",
        "reachable_pta_edges",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process_model_trace_set(
    model_trace_set: ModelTraceSet,
    pta_builder,
    pta_root: Path,
    trace_copy_root: Path,
) -> dict[str, object]:
    base_output_dir = pta_root / model_trace_set.rel_model_dir
    base_trace_dir = trace_copy_root / model_trace_set.family / "PTA" / "source_traces" / "MELA" / model_trace_set.rel_model_dir.name
    output_dir, trace_dir = versioned_output_pair(base_output_dir, base_trace_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    trace_dir.mkdir(parents=True, exist_ok=False)

    source_files = [str(path) for path in model_trace_set.source_traces]
    copied_trace_paths: list[str] = []
    for trace_path in model_trace_set.source_traces:
        copied_trace_name = "trace_literal.txt" if trace_path.name.endswith("trace_literal.txt") else "full_history_trace.txt"
        copied_trace = trace_dir / copied_trace_name
        shutil.copy2(trace_path, copied_trace)
        copied_trace_paths.append(str(copied_trace))

    logging.info(
        "Building PTA for %s/%s from %s",
        model_trace_set.family,
        model_trace_set.case_key,
        ", ".join(copied_trace_paths),
    )

    samples = []
    for trace_path in [Path(p) for p in copied_trace_paths]:
        samples.extend(pta_builder.load_samples_from_file(str(trace_path)))

    moore_pta = pta_builder.build_moore_pta(samples)
    reachable_states, reachable_edges = pta_builder.count_states_edges(moore_pta)

    dot_path = output_dir / "pta_moore.dot"
    pta_builder.save_dot_compat(moore_pta, str(dot_path))

    summary_path = output_dir / "pta_summary.txt"
    write_original_pta_summary(
        summary_path,
        copied_trace_paths,
        len(samples),
        reachable_states,
        reachable_edges,
        dot_path,
    )

    pdf_path = output_dir / "pta_moore.pdf"
    pta_builder.render_dot_to_pdf(str(dot_path), str(pdf_path))

    return {
        "family": model_trace_set.family,
        "case_key": model_trace_set.case_key,
        "model_trace_set": str(model_trace_set.rel_model_dir),
        "source_dot": str(model_trace_set.source_dot),
        "source_trace_paths": source_files,
        "copied_trace_paths": copied_trace_paths,
        "pta_output_dir": str(output_dir),
        "pta_dot": str(dot_path),
        "pta_pdf": str(pdf_path),
        "pta_summary_txt": str(summary_path),
        "sample_count": len(samples),
        "reachable_pta_states": reachable_states,
        "reachable_pta_edges": reachable_edges,
    }


def csv_ready(row: dict[str, object]) -> dict[str, object]:
    converted = dict(row)
    for key in ("source_trace_paths", "copied_trace_paths"):
        value = converted[key]
        if isinstance(value, list):
            converted[key] = " | ".join(str(item) for item in value)
    return converted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Moore PTA outputs for GSM model traces using the provided AALpy PTA code."
    )
    parser.add_argument("--pta-root", type=Path, default=PTA_ROOT)
    parser.add_argument("--trace-copy-root", type=Path, default=TRACE_COPY_ROOT)
    parser.add_argument("--provided-builder", type=Path, default=PROVIDED_PTA_BUILDER)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pta_root = args.pta_root.resolve()
    trace_copy_root = args.trace_copy_root.resolve()

    log_path = configure_logging(pta_root)
    pta_builder = load_provided_pta_builder(args.provided_builder)
    model_trace_sets = discover_model_trace_sets(family_training_roots())
    logging.info("Discovered %d GSM model trace sets", len(model_trace_sets))

    rows = [
        process_model_trace_set(model_trace_set, pta_builder, pta_root, trace_copy_root)
        for model_trace_set in model_trace_sets
    ]

    summary_csv = versioned_path(pta_root / "summaries" / "pta_build_summary.csv")
    write_summary_csv(summary_csv, (csv_ready(row) for row in rows))

    logging.info("Wrote summary CSV: %s", summary_csv)
    print(f"Built {len(rows)} PTA Moore machines")
    print(f"Summary CSV: {summary_csv}")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()

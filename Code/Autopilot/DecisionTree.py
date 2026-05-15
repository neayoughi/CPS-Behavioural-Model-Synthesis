from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text


learning_sets = ["ascend", "descend"]
configurations = ["pitchwheel", "throttle", "pitchwheel_throttle"]

target_column = "State"
features_by_configuration = {
    "pitchwheel": ["Pwheel"],
    "throttle": ["Throttle"],
    "pitchwheel_throttle": ["Pwheel", "Throttle"],
}


def find_project_root(start: Path) -> Path:
    for candidate in (start.resolve().parent, *start.resolve().parents):
        if (candidate / "Code").is_dir() and (candidate / "Data").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate project root from {start}")


project_root = find_project_root(Path(__file__))


def project_path(relative_path: str) -> Path:
    return project_root / relative_path


def train_decision_tree(df: pd.DataFrame, features: list[str]) -> DecisionTreeClassifier:
    columns = features + [target_column]
    data = df[columns].copy()
    for feature in features:
        data[feature] = pd.to_numeric(data[feature], errors="coerce")
    data[target_column] = data[target_column].astype(str).str.strip()
    data = data.dropna()

    max_leaf_nodes = 3 if len(features) == 1 else 5
    tree = DecisionTreeClassifier(
        max_leaf_nodes=max_leaf_nodes,
        random_state=42,
        class_weight="balanced",
    )
    tree.fit(data[features], data[target_column])
    return tree


def write_rules(learning_set: str, configuration: str) -> None:
    # MELA only: decision-tree rules encode the ML-learned split boundaries for MELA.
    # Baseline uses fixed manual thresholds (Pwheel: -10/10, Throttle: 0.333/0.667)
    # defined directly in Baseline_Abstraction.py — no decision-tree rules are generated for it.
    abstraction_file_path = f"Data/Autopilot/Abstraction/MELA/{learning_set}/{configuration}.csv"
    rules_file_path = f"Data/Autopilot/DecisionTree/{learning_set}/{configuration}_rules.txt"

    abstraction_path = project_path(abstraction_file_path)
    rules_path = project_path(rules_file_path)

    if not abstraction_path.exists():
        print(f"Skipping missing abstraction file: {abstraction_file_path}")
        return

    features = features_by_configuration[configuration]
    df = pd.read_csv(abstraction_path)
    tree = train_decision_tree(df, features)
    rules = export_text(tree, feature_names=features, decimals=6)

    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(
        f"Balanced tree rules for {configuration}\n"
        f"learning_set = {learning_set}\n"
        "class_weight = balanced\n\n"
        f"{rules}",
        encoding="utf-8",
    )
    print(f"Wrote {rules_file_path}")


def main() -> None:
    for learning_set in learning_sets:
        for configuration in configurations:
            write_rules(learning_set, configuration)


if __name__ == "__main__":
    main()

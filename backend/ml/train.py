"""
train.py  (ml/ directory)
XGBoost training script for the optional ML classifier.

Usage:
    python ml/train.py --data ml/data/features/labeled_features.csv --output backend/app/services/ml/model/xgboost_v1.pkl

The CSV must have columns matching EXPECTED_FEATURE_NAMES (from feature_extractor.py)
plus a "label" column with one of:
    No Discrepancy | Omission | Commission | Inconsistency | Illegibility
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
from xgboost import XGBClassifier

LABEL_CLASSES = ["No Discrepancy", "Omission", "Commission", "Inconsistency", "Illegibility"]

FEATURE_COLS = [
    "has_patient_name",
    "has_patient_age",
    "has_doctor_name",
    "has_signature",
    "has_date",
    "has_diagnosis",
    "drug_count",
    "missing_dose_count",
    "missing_freq_count",
    "missing_duration_count",
    "has_invalid_freq",
    "ocr_confidence",
    "illegible_field_count",
    "drug_not_in_rxnorm_count",
    "dose_error_count",
    "interaction_count",
]


def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")
    if "label" not in df.columns:
        raise ValueError("CSV must have a 'label' column")

    X = df[FEATURE_COLS].fillna(0).values.astype(np.float32)
    le = LabelEncoder()
    le.fit(LABEL_CLASSES)
    y = le.transform(df["label"].values)
    return X, y, le


def train(csv_path: str, output_path: str, n_folds: int = 5):
    print(f"[train] Loading data from {csv_path}")
    X, y, le = load_data(csv_path)
    print(f"[train] Dataset: {X.shape[0]} samples, {X.shape[1]} features")
    print(f"[train] Class distribution:\n{pd.Series(le.inverse_transform(y)).value_counts()}")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

    # Cross-validation
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="f1_weighted")
    print(f"[train] CV F1 (weighted): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Final fit on full data
    model.fit(X, y)

    # Evaluation on full training set (report only — use separate test set in prod)
    y_pred = model.predict(X)
    print("\n[train] Classification Report (train set):")
    print(classification_report(y, y_pred, target_names=le.classes_))

    # Feature importances
    importances = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))
    top = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print("\n[train] Top feature importances:")
    for name, imp in top[:8]:
        print(f"  {name}: {imp:.4f}")

    # Save model + metadata
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out)

    meta = {
        "cv_f1_mean": float(cv_scores.mean()),
        "cv_f1_std": float(cv_scores.std()),
        "n_samples": int(X.shape[0]),
        "feature_cols": FEATURE_COLS,
        "label_classes": list(le.classes_),
        "feature_importances": importances,
    }
    meta_path = out.parent / "xgboost_v1_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    print(f"\n[train] Model saved → {out}")
    print(f"[train] Metadata saved → {meta_path}")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to labeled_features.csv")
    parser.add_argument(
        "--output",
        default="backend/app/services/ml/model/xgboost_v1.pkl",
        help="Output path for trained model",
    )
    parser.add_argument("--folds", type=int, default=5, help="CV folds")
    args = parser.parse_args()
    train(args.data, args.output, args.folds)
"""Lightweight model placeholder.

This module trains a tiny LogisticRegression on synthetic data if no
`models/model.pkl` exists. It exposes `predict_proba_features(feature_vector)`
which returns a dict {'down': p0, 'up': p1}.

This is intentionally simple — replace with your own saved model.
"""
import os
import json
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

BASE_DIR = os.path.dirname(__file__) or "."
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

def _ensure_model():
    if os.path.exists(MODEL_PATH):
        return
    # create synthetic training data
    rng = np.random.RandomState(42)
    X = rng.randn(1000, 5)
    # target: up when sum(X) + noise > 0
    y = (X.sum(axis=1) + rng.randn(1000) * 0.5 > 0).astype(int)
    clf = LogisticRegression()
    clf.fit(X, y)
    joblib.dump(clf, MODEL_PATH)

def predict_proba_features(feature_vector):
    """Return probability of [down, up] as dict.

    `feature_vector` expected as iterable of length 5.
    """
    try:
        _ensure_model()
        clf = joblib.load(MODEL_PATH)
        X = np.array(feature_vector, dtype=float).reshape(1, -1)
        probs = clf.predict_proba(X)[0]
        return {"down": float(probs[0]), "up": float(probs[1])}
    except Exception:
        return {"down": 0.5, "up": 0.5}

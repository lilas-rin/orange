"""病虫害风险预测：随机森林分类器（低/中/高三分类）。

特征: 月份、季节、县区编码、种植面积、近12个月发生次数、近12个月影响面积、
      近12个月加权严重度。标签: 当期该县区风险等级。
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

SEVERITY_W = {"mild": 1, "moderate": 2, "severe": 3}
LEVELS = ["low", "medium", "high"]


def label_from_severity(sev_str: str) -> str:
    return {"mild": "low", "moderate": "medium", "severe": "high"}.get(sev_str, "low")


class PestRiskClassifier:
    name = "pest_risk_rf"
    algorithm = "RandomForestClassifier"

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=300, max_depth=10, class_weight="balanced", random_state=42
        )
        self.accuracy = None
        self.f1 = None
        self.feature_names = [
            "month",
            "season",
            "county_idx",
            "planting_area",
            "hist_count_12m",
            "hist_area_12m",
            "hist_severity_12m",
        ]

    def fit(self, X: np.ndarray, y: np.ndarray) -> "PestRiskClassifier":
        if len(X) < 10:
            raise ValueError("训练样本不足")
        split = max(1, int(len(X) * 0.8))
        self.model.fit(X[:split], y[:split])
        if len(X) - split >= 2:
            val_pred = self.model.predict(X[split:])
            self.accuracy = float(accuracy_score(y[split:], val_pred))
            self.f1 = float(f1_score(y[split:], val_pred, average="macro"))
        self.model.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> list[dict]:
        proba = self.model.predict_proba(X)
        classes = list(self.model.classes_)
        return [
            {c: float(p[classes.index(c)]) if c in classes else 0.0 for c in LEVELS}
            for p in proba
        ]

    def predict(self, X: np.ndarray) -> list[str]:
        return [str(v) for v in self.model.predict(X)]

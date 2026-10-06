"""产季月度序列预测器。

与 PriceForecaster 同构（滞后特征 + 滚动均值 + 随机森林回归），但把时间坐标从
「自然月」换成「产季序 × 产季内月序」：

    产季序 season：0=2020 产季，1=2021 产季 …
    产季内月序 month：1=11月，2=12月，3=次年1月 … 11=次年9月

这么做的好处是彻底绕开产季之间的月份空档（10 月）。脐橙 10 月基本无销量，
若按自然月外推，模型必须先预测一个接近 0 的 10 月，再拿这个错误的滞后值去推
新产季 11 月，误差会被成倍放大。改用产季月序后，可以直接从「去年 11 月」一步
跨到「今年 11 月」。
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error

FEATURES = ["season", "month", "lag1", "lag2", "roll3", "prev_same", "prev_prev_same"]


def season_index(year: int) -> int:
    """产季年 → 产季序（以 2020 产季为 0）。"""
    return year - 2020


def season_month(month: int) -> int:
    """自然月 → 产季内月序（11月=1 … 次年9月=11）。"""
    return month - 10 if month >= 11 else month + 2


class SeasonMonthForecaster:
    name = "orange_season_rf"
    algorithm = "RandomForestRegressor"

    def __init__(self, n_estimators: int = 240, max_depth: int = 9, min_samples_leaf: int = 2):
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=42,
        )
        self.residual_std = 0.0
        self.mape: float | None = None

    # ---------- 特征 ----------

    @staticmethod
    def build_frame(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
        """rows: [(season, month, value)]，按 (season, month) 升序。"""
        df = pd.DataFrame(rows, columns=["season", "month", "value"]).astype(float)
        df = df.sort_values(["season", "month"], kind="stable").reset_index(drop=True)
        df["lag1"] = df["value"].shift(1)
        df["lag2"] = df["value"].shift(2)
        df["roll3"] = df["value"].shift(1).rolling(3).mean()
        # 上一产季 / 上上产季的同月值（同月序列内位移，天然对齐产季）
        df["prev_same"] = df.groupby("month")["value"].shift(1)
        df["prev_prev_same"] = df.groupby("month")["value"].shift(2)
        return df

    def fit(self, rows: list[tuple[int, int, float]]) -> "SeasonMonthForecaster":
        df = self.build_frame(rows)
        train = df.dropna(subset=["prev_same"]).copy()
        # 滞后特征在产季首月会缺失，用同月序列回填，避免样本被大量丢弃
        train["lag1"] = train["lag1"].fillna(train["prev_same"])
        train["lag2"] = train["lag2"].fillna(train["prev_prev_same"]).fillna(train["prev_same"])
        train["roll3"] = train["roll3"].fillna(train["prev_same"])
        train = train.dropna(subset=FEATURES + ["value"])
        if len(train) < 12:
            raise ValueError("训练样本不足（至少 12 条产季月度记录）")

        X = train[FEATURES].values
        y = train["value"].values
        split = max(6, int(len(X) * 0.85))
        self.model.fit(X[:split], y[:split])
        preds = self.model.predict(X)
        self.residual_std = float(np.std(y - preds))
        if len(X) - split >= 3:
            self.mape = float(mean_absolute_percentage_error(y[split:], preds[split:]))
        self.model.fit(X, y)
        self._df = df
        return self

    def predict_next_season_month(self, season: int, month: int) -> tuple[float, float, float]:
        """预测指定产季、指定产季月序的值。返回 (value, lower, upper)。

        调用前必须 fit；所需的历史特征全部取自训练集，不依赖调用方补参。
        """
        hist = self._df
        prev_same = hist[(hist["season"] == season - 1) & (hist["month"] == month)]
        prev_prev = hist[(hist["season"] == season - 2) & (hist["month"] == month)]
        last3 = hist.tail(3)
        base = float(prev_same["value"].iloc[0]) if len(prev_same) else float(hist["value"].iloc[-1])
        row = [
            float(season),
            float(month),
            float(last3["value"].iloc[-1]) if len(last3) else base,
            float(last3["value"].iloc[-2]) if len(last3) > 1 else base,
            float(last3["value"].mean()) if len(last3) else base,
            base,
            float(prev_prev["value"].iloc[0]) if len(prev_prev) else base,
        ]
        raw = float(self.model.predict(np.array([row], dtype=float))[0])
        # 保底：预测值不应低于上产季同月的 40%，避免小样本树外推出极端低值
        value = max(raw, base * 0.4)
        margin = max(1.96 * self.residual_std, base * 0.06)
        return round(value, 2), round(max(0.0, value - margin), 2), round(value + margin, 2)


def holt_linear(
    values: list[float], steps: int = 1, alpha: float = 0.65, beta: float = 0.35
) -> tuple[float, float]:
    """Holt 线性趋势外推（含阻尼）。返回 (预测值, 拟合残差标准差)。

    用于产季总量这类「样本点少、单调趋势明显」的序列。
    """
    if len(values) < 3:
        raise ValueError("Holt 外推至少需要 3 个观测点")
    level = values[0]
    trend = values[1] - values[0]
    resid: list[float] = []
    for v in values[1:]:
        forecast = level + trend
        resid.append(v - forecast)
        new_level = alpha * v + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        level, trend = new_level, new_trend
    damped = trend
    pred = level
    for _ in range(steps):
        damped *= 0.75  # 阻尼，抑制线性外推失控（产季总量近年增速在放缓）
        pred = pred + damped
    std = float(np.std(resid)) if resid else 0.0
    return float(pred), std

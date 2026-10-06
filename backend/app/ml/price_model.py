"""价格预测模型：随机森林 + 时间滞后特征，递归多步预测，输出预测区间。

特征: 月份、季度、时间索引、滞后1/2期、3期滑动均值。
区间: 训练集残差分位数 ±1.96σ 近似。
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error


class PriceForecaster:
    name = "orange_price_rf"
    algorithm = "RandomForestRegressor"

    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=300, max_depth=8, min_samples_leaf=2, random_state=42
        )
        self.residual_std = 0.0
        self.mape = None

    @staticmethod
    def _features(series: pd.Series) -> pd.DataFrame:
        df = pd.DataFrame({"value": series.astype(float)})
        df["month"] = series.index.month
        df["quarter"] = (series.index.month - 1) // 3 + 1
        df["t"] = np.arange(len(series))
        df["lag1"] = df["value"].shift(1)
        df["lag2"] = df["value"].shift(2)
        df["roll3"] = df["value"].shift(1).rolling(3).mean()
        return df

    def fit(self, series: pd.Series) -> "PriceForecaster":
        """series: 以月初(Period/Timestamp)为索引的月度价格序列。"""
        feat = self._features(series).dropna()
        X = feat[["month", "quarter", "t", "lag1", "lag2", "roll3"]].values
        y = feat["value"].values
        if len(X) < 8:
            raise ValueError("训练样本不足（至少8个月）")
        split = max(1, int(len(X) * 0.85))
        self.model.fit(X[:split], y[:split])
        # 残差分布（含验证段），用于预测区间
        preds_all = self.model.predict(X)
        self.residual_std = float(np.std(y - preds_all))
        if len(X) - split >= 2:
            self.mape = float(mean_absolute_percentage_error(y[split:], preds_all[split:]))
        # 最终用全量数据重训
        self.model.fit(X, y)
        return self

    def forecast(self, series: pd.Series, steps: int) -> list[dict]:
        """递归多步预测。返回 [{month: 'YYYY-MM', value, lower, upper}]"""
        history = series.copy().astype(float)
        out = []
        margin = 1.96 * self.residual_std
        for _ in range(steps):
            feat = self._features(history)
            row = feat.iloc[-1][["month", "quarter", "t", "lag1", "lag2", "roll3"]]
            nxt = float(self.model.predict(row.values.reshape(1, -1))[0])
            next_period = history.index[-1] + 1  # 月度 Period
            out.append(
                {
                    "month": str(next_period),
                    "value": round(nxt, 2),
                    "lower": round(max(0.0, nxt - margin), 2),
                    "upper": round(nxt + margin, 2),
                }
            )
            history.loc[next_period] = nxt
        return out

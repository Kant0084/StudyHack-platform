"""合成示例数据生成。

仅用于 demo 与测试：生成结构可控的模拟面板数据，便于演示
「数据 → 回归 → 三线表」全流程，不依赖外部数据源。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_finance_panel(
    n_firms: int = 120,
    n_years: int = 5,
    seed: int = 42,
) -> pd.DataFrame:
    """生成公司金融模拟面板数据。

    数据生成机制（教学演示用，非真实经济关系）：
      - 每个公司存在不可观测的固定效应 firm_fe（如管理层能力）；
      - lev 与 firm_fe 正相关（存在内生性，适合演示固定效应回归）；
      - roa 由 lev/size/growth/cash + firm_fe + 噪声 线性决定。

    返回列：firm_id, year, roa(因变量), lev, size, growth, cash。
    """
    rng = np.random.default_rng(seed)
    rows = []
    for firm in range(n_firms):
        firm_fe = rng.normal(0.0, 0.5)  # 公司固定效应
        for year in range(n_years):
            lev = 0.5 + 0.3 * firm_fe + rng.normal(0.0, 0.2)  # 杠杆率（与固定效应相关）
            size = rng.normal(10.0, 1.5)                       # 企业规模（对数总资产）
            growth = rng.normal(0.1, 0.3)                      # 营收增速
            cash = rng.normal(0.15, 0.1)                       # 现金持有
            e = rng.normal(0.0, 0.3)                           # 噪声
            roa = 0.10 + (-0.15) * lev + 0.01 * size + 0.02 * growth + 0.05 * cash + firm_fe + e
            rows.append(
                {
                    "firm_id": f"F{firm:04d}",
                    "year": 2016 + year,
                    "roa": roa,
                    "lev": lev,
                    "size": size,
                    "growth": growth,
                    "cash": cash,
                }
            )
    return pd.DataFrame(rows)

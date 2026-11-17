"""公司金融示例（erk demo finance）。

演示完整链路：合成数据 → 三个逐步加严的基准回归 → 三线表渲染与输出。
"""

from __future__ import annotations

from pathlib import Path

from erk.config import Config
from erk.data.synthetic import generate_finance_panel
from erk.report.table import RegressionTable
from erk.stats.regression import run_ols


def run_demo(cfg: Config) -> None:
    print("=" * 60)
    print("erk demo finance · 公司金融基准回归示例")
    print("=" * 60)

    # 1. 数据
    df = generate_finance_panel(n_firms=120, n_years=5, seed=42)
    print(f"[1/3] 生成模拟面板数据: {df.shape[0]} 行 × {df.shape[1]} 列")

    # 2. 三个逐步加严的模型
    r1 = run_ols(df, "roa", ["lev"], label="(1)")
    r2 = run_ols(df, "roa", ["lev", "size", "growth", "cash"], label="(2)")
    r3 = run_ols(
        df,
        "roa",
        ["lev", "size", "growth", "cash"],
        fe=["firm_id", "year"],
        cluster="firm_id",
        label="(3)",
    )
    print("[2/3] 完成 3 个基准回归")

    # 3. 渲染与输出
    table = RegressionTable([r1, r2, r3], cfg, title="表1 基准回归结果（被解释变量：ROA）")
    print("\n" + table.render_console())

    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "finance_regression.md"
    xlsx_path = out / "finance_regression.xlsx"
    md_path.write_text(table.render_markdown(), encoding="utf-8")
    table.to_excel(xlsx_path)

    print(f"\n[3/3] 结果已输出:")
    print(f"  - {md_path}")
    print(f"  - {xlsx_path}")

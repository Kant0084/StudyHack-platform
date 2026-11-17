"""问卷分析示例（erk demo survey）。

生成含 3 个潜变量（各 4 题）的 Likert 量表数据，演示信效度检验全流程。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from erk.config import Config
from erk.survey.dataset import QuestionnaireDataset


def generate_likert_data(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """生成含 3 个潜变量的 Likert 量表数据。

    数据生成机制（教学演示）：
      - 3 个潜变量 factor_0/1/2，每个对应 4 个题项；
      - 题项 = 0.8·潜变量 + 噪声，映射到 Likert 1–5 分；
      - 同一量表内部题项高相关 → Cronbach's α 应较高（≈0.84）。
    """
    rng = np.random.default_rng(seed)
    data = {}
    for f in range(3):
        factor = rng.normal(0.0, 1.0, n)
        for i in range(4):
            score = 0.8 * factor + rng.normal(0.0, 0.7, n)
            likert = np.clip(np.round(3 + score), 1, 5).astype(int)
            data[f"Q{f + 1}{i + 1}"] = likert
    return pd.DataFrame(data)


def run_demo(cfg: Config) -> None:
    print("=" * 60)
    print("erk demo survey · 问卷信效度分析示例")
    print("=" * 60)

    df = generate_likert_data()
    ds = QuestionnaireDataset(df)
    print(f"[1/3] 生成量表数据: {ds.n_samples} 份 × {len(ds.columns)} 题")

    cols = ["Q11", "Q12", "Q13", "Q14"]
    print(f"[2/3] 量表 {cols} 信效度检验...")
    rel = ds.reliability(cols)

    alpha_judge = "良好" if rel.alpha_good else ("可接受" if rel.alpha_ok else "偏低")
    print(f"\nCronbach's α = {rel.alpha:.3f}（{alpha_judge}）")
    print(f"KMO = {rel.kmo:.3f}（{'可接受' if rel.kmo_ok else '偏低'}）")
    print(f"Bartlett χ² = {rel.bartlett_chi2:.2f}, df={rel.bartlett_df}, p={rel.bartlett_p:.4f}")

    print("\n项总计相关 & 删除后 α:")
    for i, col in enumerate(cols):
        print(f"  {col}: item-total={rel.item_total[i]:.3f}, α-if-deleted={rel.alpha_if_deleted[i]:.3f}")

    print("\n[3/3] 描述统计:")
    print(ds.descriptives(cols).to_string())

    r = ds.correlate("Q11", "Q12")
    print(f"\nQ11–Q12 皮尔逊相关: r={r.statistic:.3f}, p={r.p_value:.4f}")

    # EFA：对全部 12 个题项提取 3 个因子
    from erk.survey.factor_analysis import factor_analysis

    all_cols = [f"Q{f + 1}{i + 1}" for f in range(3) for i in range(4)]
    fa = factor_analysis(ds.data[all_cols].to_numpy(float), n_factors=3, item_labels=all_cols)
    print(f"\n[EFA] 提取 {fa.n_factors} 个因子，累积方差解释率 = {fa.total_variance_explained:.1%}")
    L = np.asarray(fa.loadings)
    print("  载荷矩阵（行=题项，列=因子）:")
    print("    " + "".join(f"因子{i + 1:<9}" for i in range(fa.n_factors)))
    for i, col in enumerate(all_cols):
        print(f"    {col:<6}" + "".join(f"{L[i, j]:<9.3f}" for j in range(fa.n_factors)))

    # agent 档输出（含风险提示与阈值出处）
    print("\n--- agent 档信封（节选）---")
    d = rel.to_dict("agent")
    for w in d.get("warnings", []):
        print(f"  [提示] {w}")
    print("  阈值依据:", d.get("thresholds", {}))

    # 生成完整报告
    from pathlib import Path

    from erk.report.survey_report import build_survey_report

    # 生成完整报告（对第一个量表 Q11–Q14 做完整信效度）
    report = build_survey_report(ds, scale_cols=cols)
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = report.save(out / "survey_report.md")
    docx_path = report.save(out / "survey_report.docx")
    print(f"\n[报告] 已生成完整问卷分析报告:")
    print(f"  - {md_path}")
    print(f"  - {docx_path}")

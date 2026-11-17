"""ERK 命令行入口。

子命令：
  erk demo <finance|survey>   运行官方示例
  erk load <file>             导入并检查原始数据
  erk template [name]         查看/选择分析模板
  erk run [options]           执行分析流程（v0.2 完整实现）

设计说明：CLI 只做「参数解析 + 流程编排」，具体逻辑下沉到
data / stats / report 各模块，保持薄入口、厚模块。
"""

from __future__ import annotations

import argparse
import sys

from erk import __version__
from erk.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="erk",
        description="empirical-research-kit · 社科经管实证研究全流程自动化工具包",
    )
    parser.add_argument("-V", "--version", action="version", version=f"erk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # erk demo
    p_demo = sub.add_parser("demo", help="运行官方示例")
    p_demo.add_argument(
        "name",
        choices=["finance", "survey"],
        nargs="?",
        default="finance",
        help="示例名称：finance(公司金融) / survey(问卷分析)",
    )

    # erk load
    p_load = sub.add_parser("load", help="导入并检查原始数据")
    p_load.add_argument("file", help="数据文件路径（.xlsx/.csv/.dta）")

    # erk template
    p_tmpl = sub.add_parser("template", help="查看/选择分析模板")
    p_tmpl.add_argument("name", nargs="?", default=None, help="模板名称（留空列出全部）")

    # erk run
    p_run = sub.add_parser("run", help="执行分析流程")
    p_run.add_argument("--template", "-t", help="使用的分析模板")
    p_run.add_argument("--data", "-d", help="数据文件路径")
    p_run.add_argument("--output", "-o", default=None, help="结果输出目录")

    # erk method
    p_method = sub.add_parser("method", help="识别策略决策树（推荐方法）")
    p_method.add_argument("--panel", action="store_true", help="是否有面板数据")
    p_method.add_argument("--time", action="store_true", help="是否有政策前后时间维")
    p_method.add_argument("--treatment", action="store_true", help="是否有处理组/对照组")
    p_method.add_argument("--instrument", action="store_true", help="是否有工具变量")
    p_method.add_argument("--cutoff", action="store_true", help="是否有断点/阈值规则")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()

    if args.command == "demo":
        return _cmd_demo(args, cfg)
    if args.command == "load":
        return _cmd_load(args)
    if args.command == "template":
        return _cmd_template(args)
    if args.command == "run":
        return _cmd_run(args, cfg)
    if args.command == "method":
        return _cmd_method(args)
    return 0


def _cmd_demo(args, cfg) -> int:
    if args.name == "finance":
        from erk.demo.finance import run_demo

        run_demo(cfg)
        return 0
    if args.name == "survey":
        from erk.demo.survey import run_demo

        run_demo(cfg)
        return 0
    return 0


def _cmd_load(args) -> int:
    from erk.data.loader import load_file

    df = load_file(args.file)
    print(f"[load] 已加载 {args.file}")
    print(f"[load] 形状: {df.shape[0]} 行 × {df.shape[1]} 列")
    print("[load] 列名:", list(df.columns))
    return 0


def _cmd_template(args) -> int:
    from erk.templates import describe_template, get_template, list_templates

    if args.name is None:
        print("可用模板:")
        for name in list_templates():
            t = get_template(name)
            print(f"  - {name:<10} {t.title if t else ''}")
    else:
        print(describe_template(args.name))
    return 0


def _cmd_method(args) -> int:
    from erk.templates import recommend_method

    recs = recommend_method(
        has_panel=args.panel,
        has_time=args.time,
        has_treatment=args.treatment,
        has_instrument=args.instrument,
        has_cutoff=args.cutoff,
    )
    print("推荐识别策略（按优先级）:")
    for i, r in enumerate(recs, 1):
        print(f"\n{i}. {r.name.upper()} — {r.reason}")
        print("   必查诊断:")
        for c in r.checks:
            print(f"     - {c}")
        print(f"   出处: {', '.join(r.references)}")
    return 0


def _cmd_run(args, cfg) -> int:
    """执行分析流程（v0.1 最小可用：finance 模板基准回归闭环）。"""
    from pathlib import Path

    tmpl = args.template or "finance"
    if tmpl != "finance":
        print(f"[run] 模板「{tmpl}」的完整编排尚未实现，当前仅支持 finance。")
        print("[run] 其余模板(did/iv/rdd/psm)规划中，可先运行 `erk demo finance` 体验完整链路。")
        return 0

    # 1. 数据：--data 指定文件，否则用合成示例数据
    if args.data:
        from erk.data.loader import load_file

        try:
            df = load_file(args.data)
        except Exception as exc:  # noqa: BLE001
            print(f"[run] 数据加载失败: {exc}")
            return 1
        print(f"[run] 已加载数据 {args.data}: {df.shape[0]} 行 × {df.shape[1]} 列")
    else:
        from erk.data.synthetic import generate_finance_panel

        df = generate_finance_panel()
        print(f"[run] 使用合成示例面板数据: {df.shape[0]} 行 × {df.shape[1]} 列")

    # 2. 校验必需变量
    required = ["roa", "lev", "size", "firm_id", "year"]
    missing = [v for v in required if v not in df.columns]
    if missing:
        print(f"[run] 数据缺少必需变量 {missing}。现有列: {list(df.columns)}")
        return 1

    # 3. 基准回归（OLS → 加控制变量 → FE + 聚类）
    from erk.report.table import RegressionTable
    from erk.stats.regression import run_ols

    extra = [c for c in ("growth", "cash") if c in df.columns]
    r1 = run_ols(df, "roa", ["lev"], label="(1)")
    r2 = run_ols(df, "roa", ["lev", "size"] + extra, label="(2)")
    r3 = run_ols(
        df,
        "roa",
        ["lev", "size"] + extra,
        fe=["firm_id", "year"],
        cluster="firm_id",
        label="(3)",
    )
    table = RegressionTable([r1, r2, r3], cfg, title="表1 基准回归结果（被解释变量：ROA）")
    print("\n" + table.render_console())

    # 4. 输出
    out = Path(args.output or cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "regression.md").write_text(table.render_markdown(), encoding="utf-8")
    table.to_excel(out / "regression.xlsx")
    print(f"\n[run] 结果已输出: {out / 'regression.md'} / {out / 'regression.xlsx'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

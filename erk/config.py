"""配置系统。

设计原则：
  - 开箱即用：提供默认配置，零配置即可跑通 demo；
  - 用户级覆盖：读取 ~/.erk/config.json 覆盖默认值；
  - 集中管理：所有可调项（软件路径、表格样式、显著性规则）集中于此，
    避免配置散落各处。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_FILE = Path.home() / ".erk" / "config.json"


@dataclass
class SoftwarePaths:
    """三大专业软件的可执行路径。留空表示未安装，进阶分析会自动跳过。"""

    stata: str = ""  # Stata 可执行文件路径，如 "C:/Program Files/Stata18/StataMP-64.exe"
    r: str = ""      # Rscript 路径，如 "Rscript"
    spss: str = ""   # SPSS 安装目录


@dataclass
class TableStyle:
    """三线表排版风格，符合中文期刊规范。"""

    decimals: int = 3                        # 系数/标准误小数位
    sig_levels: tuple = (0.01, 0.05, 0.1)    # 显著性阈值（1% / 5% / 10%）
    sig_symbols: tuple = ("***", "**", "*")  # 对应星号标注


@dataclass
class Config:
    """全局配置。"""

    software: SoftwarePaths = field(default_factory=SoftwarePaths)
    table: TableStyle = field(default_factory=TableStyle)
    output_format: str = "excel"       # 结果默认导出格式：excel / markdown / console
    output_dir: str = "./erk_output"   # 默认输出目录


def default_config() -> Config:
    """返回默认配置。"""
    return Config()


def load_config(path: str | Path | None = None) -> Config:
    """加载配置：优先读用户配置文件，缺失字段回退默认值。

    配置文件损坏时回退默认配置并给出告警，不阻断主流程。
    """
    cfg = default_config()
    fp = Path(path) if path else DEFAULT_CONFIG_FILE
    if fp.exists():
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            _merge(cfg, data)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[warn] 配置文件解析失败，使用默认配置: {exc}")
    return cfg


def _merge(cfg: Config, data: dict) -> None:
    """将 JSON 字典合并进配置，仅覆盖已声明的字段，忽略未知键。"""
    for key, value in data.items():
        if not hasattr(cfg, key):
            continue
        cur = getattr(cfg, key)
        if isinstance(cur, (SoftwarePaths, TableStyle)) and isinstance(value, dict):
            for k, v in value.items():
                if hasattr(cur, k):
                    setattr(cur, k, v)
        else:
            setattr(cfg, key, value)

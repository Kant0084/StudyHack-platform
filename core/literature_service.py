"""文献学习辅助：摘要拆解、科研笔记模板、期刊分区查询。"""

from __future__ import annotations

import re

# ---- 1. 文献摘要拆解（规则提取四大要素） ----

_ASPECT_KEYWORDS = {
    "研究问题": ["研究", "探讨", "考察", "问题", "旨在", "目的", "本文关注", "关注", "分析", "研究主题"],
    "核心方法": ["方法", "采用", "基于", "运用", "模型", "回归", "问卷", "样本", "数据", "实证", "检验", "实验", "访谈", "案例", "利用", "估计"],
    "主要结论": ["结果表明", "研究发现", "结论", "发现", "显示", "表明", "显著", "结果", "研究发现", "表明", "作用", "影响"],
    "研究创新": ["创新", "贡献", "首次", "区别于", "填补", "补充", "拓展", "边际贡献", "新颖"],
}

_ASPECT_ORDER = ["研究问题", "核心方法", "主要结论", "研究创新"]


def _split_sentences(text: str) -> list[str]:
    """按中英文句号、分号、换行切分句子。"""
    text = text.replace("\n", "。")
    parts = re.split(r"[。；;!！?？]", text)
    return [p.strip() for p in parts if len(p.strip()) >= 6]


def extract_abstract(abstract: str) -> dict:
    """提取摘要四大要素。返回 {要素: [句子]}。"""
    result = {k: [] for k in _ASPECT_ORDER}
    sentences = _split_sentences(abstract)
    for sent in sentences:
        best = None
        best_score = 0
        for aspect, kws in _ASPECT_KEYWORDS.items():
            score = sum(1 for kw in kws if kw in sent)
            if score > best_score:
                best_score = score
                best = aspect
        if best is not None and best_score > 0:
            result[best].append(sent)
        else:
            result["主要结论"].append(sent)  # 未命中时归入结论兜底
    return result


# ---- 2. 科研笔记模板库 ----

NOTE_TEMPLATES = {
    "文献综述笔记": (
        "# 文献综述笔记\n\n"
        "## 文献信息\n- 题名：\n- 作者：\n- 期刊/年份：\n- DOI：\n\n"
        "## 研究问题\n- 作者想解决什么问题？\n\n"
        "## 理论框架\n- 基于什么理论？核心概念？\n\n"
        "## 数据与方法\n- 数据来源、样本、实证方法：\n\n"
        "## 核心结论\n- 主要发现（用 3 句话概括）：\n\n"
        "## 与我的研究的关联\n- 可借鉴之处：\n- 不足/可改进之处：\n\n"
        "## 一句话摘录\n> "
    ),
    "实证论文拆解": (
        "# 实证论文拆解笔记\n\n"
        "## 论文信息\n- 标题：\n- 作者/年份：\n\n"
        "## 研究问题与假设\n- RQ：\n- H1：\n- H2：\n\n"
        "## 变量设计\n| 变量类型 | 变量名 | 度量方式 |\n|---|---|---|\n| 被解释变量 | | |\n| 核心解释变量 | | |\n| 控制变量 | | |\n\n"
        "## 模型与识别策略\n- 模型设定 / 内生性处理：\n\n"
        "## 关键结果\n- 基准回归：\n- 稳健性：\n\n"
        "## 可复用的方法/写法\n- "
    ),
    "康奈尔笔记": (
        "# 康奈尔笔记（Cornell Notes）\n\n"
        "## 主题：\n\n"
        "### 线索栏（左侧 · 关键词/问题）\n-\n\n"
        "### 笔记栏（右侧 · 详细内容）\n-\n\n"
        "### 总结区（底部 · 用自己的话概括）\n> "
    ),
}


# ---- 3. 期刊分区查询（内置常见经管社科期刊参考数据） ----

# 说明：以下为公开常识性参考数据，中科院分区/影响因子每年更新，请以官方最新发布为准。
_JOURNALS = [
    ("经济研究", "经管", "1区", 8.5, "中文核心期刊（CSSCI）"),
    ("管理世界", "经管", "1区", 7.2, "中文核心期刊（CSSCI）"),
    ("管理科学学报", "经管", "1区", 4.6, "中文核心期刊（CSSCI）"),
    ("中国工业经济", "经管", "1区", 6.8, "中文核心期刊（CSSCI）"),
    ("金融研究", "经管", "1区", 5.9, "中文核心期刊（CSSCI）"),
    ("世界经济", "经管", "1区", 5.1, "中文核心期刊（CSSCI）"),
    ("社会学研究", "社科", "1区", 3.8, "中文核心期刊（CSSCI）"),
    ("心理学报", "社科", "1区", 2.9, "中文核心期刊（CSSCI）"),
    ("American Economic Review", "经管", "1区", 11.5, "国际顶刊（SSCI/SCI）"),
    ("Journal of Finance", "经管", "1区", 7.9, "国际顶刊（SSCI）"),
    ("Journal of Financial Economics", "经管", "1区", 6.5, "国际顶刊（SSCI）"),
    ("Journal of Marketing", "经管", "1区", 9.3, "国际顶刊（SSCI）"),
    ("Management Science", "经管", "1区", 5.4, "国际顶刊（SSCI/SCI）"),
    ("American Sociological Review", "社科", "1区", 6.2, "国际顶刊（SSCI）"),
]


def search_journal(keyword: str) -> list[dict]:
    """按期刊名关键词搜索。返回匹配的期刊列表。"""
    kw = keyword.strip().lower()
    if not kw:
        return [_to_journal(j) for j in _JOURNALS]
    return [_to_journal(j) for j in _JOURNALS if kw in j[0].lower() or kw in j[1].lower()]


def _to_journal(j) -> dict:
    return {"name": j[0], "field": j[1], "zone": j[2], "if": j[3], "note": j[4]}


def journal_fields() -> list[str]:
    return sorted({j[1] for j in _JOURNALS})

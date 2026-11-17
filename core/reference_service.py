"""参考文献格式转换（GB/T 7714-2015 / APA 7th / MLA 9th）。

支持中英文文献，覆盖期刊[J]、专著[M]、学位论文[D]、会议论文[C]、电子资源[EB/OL]。
作者姓名按「姓 + 名」拆分，中英文分别按对应标准格式化。
"""

from __future__ import annotations

import re

# 文献类型 → 各格式的类型标记
_TYPE_LABEL = {
    "gbt": {"J": "J", "M": "M", "D": "D", "C": "C", "EB": "EB/OL"},
    "apa": {"J": "journal article", "M": "book", "D": "dissertation", "C": "conference paper", "EB": "web page"},
}


# 常见中文姓氏拼音（用于消解英文姓名「姓/名」歧义）
_COMMON_CHINESE_SURNAMES = {
    "zhang", "wang", "li", "liu", "chen", "yang", "huang", "zhao", "wu", "zhou", "xu",
    "sun", "ma", "zhu", "hu", "guo", "he", "gao", "lin", "luo", "zheng", "liang", "xie",
    "song", "tang", "han", "cao", "deng", "xiao", "feng", "zeng", "cheng", "cai", "peng",
    "pan", "yuan", "yu", "dong", "su", "ye", "lu", "wei", "jiang", "tian", "du", "ding",
    "shen", "ren", "yao", "fan", "fang", "shi", "jin", "liao", "jia", "xia", "fu", "zou",
    "xiong", "bai", "meng", "qin", "qiu", "hou", "yin", "xue", "yan", "duan", "lei", "long",
    "tao", "ge", "gu", "hong", "ji", "kong", "lang", "lai", "wan", "wen", "xia", "chen",
}


def _is_chinese(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def parse_authors(text: str) -> list[dict]:
    """解析作者串，返回 [{last, first, zh}]。

    支持分隔符：逗号(,，)、分号(;；)、顿号(、)。
    英文姓名：含逗号按「姓, 名」；否则若首词为常见中文姓氏拼音则按「姓 名」，
    否则按英文习惯「名 姓」（末词为姓）。
    """
    if not text or not text.strip():
        return []
    parts = [p.strip() for p in re.split(r"[,，;；、]", text) if p.strip()]
    authors = []
    for p in parts:
        if _is_chinese(p):
            authors.append({"last": p, "first": "", "zh": True})
        else:
            if "," in p:
                last, first = [x.strip() for x in p.split(",", 1)]
            else:
                toks = p.split()
                if len(toks) >= 2:
                    if toks[0].lower() in _COMMON_CHINESE_SURNAMES:
                        # 中文拼音习惯：姓在前
                        last, first = toks[0], " ".join(toks[1:])
                    else:
                        # 英文习惯：名在前，姓在后
                        last, first = toks[-1], " ".join(toks[:-1])
                else:
                    last, first = p, ""
            authors.append({"last": last, "first": first, "zh": False})
    return authors


def _fmt_gbt_authors(authors: list[dict]) -> str:
    """GB/T 7714：≤3 全列，>3 列前 3 加「等」/「et al」。

    中文作者用中文逗号「，」，英文作者用英文逗号「, 」。
    """
    if not authors:
        return ""
    zh = authors[0]["zh"]
    sep = "，" if zh else ", "
    listed = authors[:3]
    parts = []
    for a in listed:
        if a["zh"]:
            parts.append(a["last"])
        else:
            first_init = "".join(t[0].upper() for t in a["first"].split()) if a["first"] else ""
            parts.append(f"{a['last'].upper()} {first_init}".strip())
    s = sep.join(parts)
    if len(authors) > 3:
        s += "，等" if zh else ", et al"
    return s


def _fmt_apa_authors(authors: list[dict]) -> str:
    """APA 7th：LastName, F. M.；英文用 & 连接最后两位，中文用「、」。"""
    if not authors:
        return ""
    zh = authors[0]["zh"]
    parts = []
    for a in authors:
        if a["zh"]:
            parts.append(a["last"])
        else:
            init = " ".join(f"{t[0].upper()}." for t in a["first"].split()) if a["first"] else ""
            parts.append(f"{a['last']}, {init}".strip())
    if len(parts) == 1:
        return parts[0]
    if zh:
        return "、".join(parts)
    return ", ".join(parts[:-1]) + ", & " + parts[-1]


def _fmt_mla_authors(authors: list[dict]) -> str:
    """MLA 9th：首位「姓, 名」，其余「名 姓」；>2 用 et al.。"""
    if not authors:
        return ""
    if len(authors) == 1:
        a = authors[0]
        return a["last"] if a["zh"] else f"{a['last']}, {a['first']}".strip()
    if len(authors) == 2:
        a, b = authors
        fa = a["last"] if a["zh"] else f"{a['last']}, {a['first']}".strip()
        fb = b["last"] if b["zh"] else f"{b['first']} {b['last']}".strip()
        return f"{fa}, and {fb}"
    a = authors[0]
    return (a["last"] if a["zh"] else f"{a['last']}, {a['first']}".strip()) + ", et al."


def _fmt_pages_gbt(pages: str) -> str:
    p = pages.strip()
    if not p:
        return ""
    return p


def format_reference(
    ref_type: str = "J",
    authors: str = "",
    year: str = "",
    title: str = "",
    source: str = "",       # 期刊名 / 出版社 / 学校
    volume: str = "",
    issue: str = "",
    pages: str = "",
    doi: str = "",
    url: str = "",
    location: str = "",     # 出版地（书籍）/ 会议地点
    degree: str = "",       # 学位
) -> dict:
    """按三种格式生成参考文献条目。

    返回 {"gbt": str, "apa": str, "mla": str}。
    """
    authors = authors.strip()
    title = title.strip()
    source = source.strip()
    year = year.strip()
    volume = volume.strip()
    issue = issue.strip()
    pages = pages.strip()
    doi = doi.strip().lstrip("https://doi.org/").lstrip("doi:")
    url = url.strip()

    al = parse_authors(authors)
    gbt_a = _fmt_gbt_authors(al)
    apa_a = _fmt_apa_authors(al)
    mla_a = _fmt_mla_authors(al)

    zh = bool(al) and al[0]["zh"]

    # ---- GB/T 7714-2015 ----
    if ref_type == "J":
        gbt = f"{gbt_a}. {title}[J]. {source}, {year}"
        if volume:
            gbt += f", {volume}"
            if issue:
                gbt += f"({issue})"
        if pages:
            gbt += f": {pages}"
        gbt += "."
    elif ref_type == "M":
        gbt = f"{gbt_a}. {title}[M]"
        if location:
            gbt += f". {location}"
        gbt += f": {source}, {year}."
    elif ref_type == "D":
        gbt = f"{gbt_a}. {title}[D]. {location or ''}{': ' if location else ''}{source}, {year}."
    elif ref_type == "C":
        gbt = f"{gbt_a}. {title}[C]//会议论文集. {location or source}, {year}: {pages or '—'}."
    else:  # EB
        gbt = f"{gbt_a}. {title}[EB/OL]. ({year})"
        if url:
            gbt += f"[{year}-01-01]. {url}"
        gbt += "."

    # ---- APA 7th ----
    y = f"({year}). " if year else "(n.d.). "
    if ref_type == "J":
        apa = f"{apa_a} {y}{title}. *{source}*"
        if volume:
            apa += f", *{volume}*"
            if issue:
                apa += f"({issue})"
        if pages:
            apa += f", {pages}"
        apa += "."
    elif ref_type == "M":
        apa = f"{apa_a} {y}*{title}*. {source}."
    elif ref_type == "D":
        apa = f"{apa_a} {y}*{title}* [{degree or 'Doctoral dissertation'}]. {source}."
    elif ref_type == "C":
        apa = f"{apa_a} {y}{title}. In *{source}* (pp. {pages or '—'}). {location or ''}."
    else:
        apa = f"{apa_a} {y}{title}. {source}. {url or ''}"

    if doi:
        apa += f" https://doi.org/{doi}"

    # ---- MLA 9th ----
    if ref_type == "J":
        mla = f"{mla_a}. \"{title}.\" *{source}*"
        if volume:
            mla += f", vol. {volume}"
        if issue:
            mla += f", no. {issue}"
        mla += f", {year}"
        if pages:
            mla += f", pp. {pages}"
        mla += "."
    elif ref_type == "M":
        mla = f"{mla_a}. *{title}*. {source}, {year}."
    elif ref_type == "D":
        mla = f"{mla_a}. \"{title}.\" {degree or 'Dissertation'}, {source}, {year}."
    elif ref_type == "C":
        mla = f"{mla_a}. \"{title}.\" *{source}*, {year}, pp. {pages or '—'}."
    else:
        mla = f"{mla_a}. \"{title}.\" *{source}*, {year}, {url or ''}."

    return {"gbt": gbt, "apa": apa, "mla": mla}


# 类型中文名（供 UI）
TYPE_OPTIONS = {
    "期刊论文 [J]": "J",
    "专著/书籍 [M]": "M",
    "学位论文 [D]": "D",
    "会议论文 [C]": "C",
    "电子资源/网页 [EB/OL]": "EB",
}

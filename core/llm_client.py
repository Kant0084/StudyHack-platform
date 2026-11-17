"""用户自有 API Key 的大模型客户端（OpenAI 兼容接口）。

通过让用户提供自己的 API Key，摆脱云服务对「来源域名」的限制，
使 AI 功能在任意部署环境（含 Streamlit Cloud）都可用。

支持任何 OpenAI 兼容接口的提供商，内置常见国产/国际厂商预设。
API Key 仅存于 Streamlit session 内存，不写盘、不持久化。
"""

from __future__ import annotations

import json

import requests

# 提供商预设（均为 OpenAI 兼容接口）
PROVIDERS: dict[str, dict] = {
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "desc": "国产 · 便宜 · 中文佳",
    },
    "通义千问 (阿里)": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "desc": "阿里 · 中文佳",
    },
    "Moonshot Kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "desc": "月之暗面 · 长文本",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "desc": "国际 · 通用",
    },
    "自定义": {
        "base_url": "",
        "model": "",
        "desc": "任意 OpenAI 兼容接口",
    },
}


def chat_stream(base_url: str, api_key: str, model: str, system: str, user: str):
    """流式调用 OpenAI 兼容的 chat/completions，逐段 yield 回复内容。

    抛出的 RuntimeError 携带可读错误信息（鉴权失败 / 额度不足 / 网络错误等）。
    """
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=180)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"网络请求失败：{exc}") from exc

    if resp.status_code != 200:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:  # noqa: BLE001
            detail = resp.text[:300]
        raise RuntimeError(f"请求失败（HTTP {resp.status_code}）：{detail}")

    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8", errors="ignore").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        content = delta.get("content")
        if content:
            yield content


# ---- 系统提示词 ----

ABSTRACT_SYSTEM = (
    "你是一名严谨的学术文献分析助手。请阅读用户提供的论文摘要，"
    "用简体中文提炼出以下四大要素，分点输出，每点用 1-2 句话概括：\n"
    "【研究问题】作者要解决的核心问题；\n"
    "【核心方法】采用的数据与研究方法；\n"
    "【主要结论】最重要的研究发现；\n"
    "【研究创新】相比既有研究的贡献或新颖之处。\n"
    "不要编造摘要中不存在的内容，若某要素未提及则标注「摘要未明确说明」。"
)

POLISH_SYSTEM = (
    "你是一名专业的学术写作润色助手。请将用户提供的口语化、生活化表述，"
    "改写为规范、严谨、客观的学术表达。要求：\n"
    "1. 保持原意不变，不使用网络流行语与主观感叹；\n"
    "2. 用词准确、句式书面化，符合社科经管论文的语言习惯；\n"
    "3. 若原文含明显逻辑或表达问题，可在改写后附一句简短说明。\n"
    "直接输出改写后的学术表述。"
)

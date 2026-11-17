"""LLM 组件（基于云服务 CDN SDK）。

通过 Streamlit `st.components.v1.html` 嵌入，前端用 CDN 加载云服务 SDK，
实现「文献摘要拆解」「学术润色」等 AI 能力（keyless，无需用户自带 key）。

注意：云服务 server 通过 Origin 精确匹配校验，故 LLM 调用在部署后的线上域名
（studyhack.app.workbuddy.host）可用；本地 localhost 开发时可能因 Origin 不匹配被拒。
"""

from __future__ import annotations

import json

from core import cloud_config

CDN_SDK = "https://cdn.jsdelivr.net/npm/@tencent-ai/workbuddy-cloud-sdk@dev/lib/index.global.js"

_HTML = """
<script src="__CDN_SDK__"></script>
<style>
  .llm-wrap { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
  .llm-wrap textarea { width: 100%; height: 130px; box-sizing: border-box; padding: 10px 12px;
    border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; resize: vertical; }
  .llm-wrap .btn { margin: 10px 0; display: inline-block; background: #2E7D6B; color: #fff;
    border: none; border-radius: 8px; padding: 8px 20px; font-size: 14px; cursor: pointer; }
  .llm-wrap .btn:hover { background: #266958; }
  .llm-wrap .btn:disabled { background: #9ca3af; cursor: not-allowed; }
  .llm-wrap #status { color: #6b7280; font-size: 13px; margin: 4px 0; }
  .llm-wrap #out { white-space: pre-wrap; background: #f4f7f6; border: 1px solid #e5e7eb;
    border-radius: 8px; padding: 12px 14px; font-size: 14px; line-height: 1.7; min-height: 80px; }
</style>
<div class="llm-wrap">
  <div style="font-weight:600;margin-bottom:6px;">__TITLE__</div>
  <textarea id="in" placeholder="__PLACEHOLDER__"></textarea>
  <div><button class="btn" id="btn" onclick="run()">__BUTTON__</button></div>
  <div id="status"></div>
  <div id="out"></div>
</div>
<script>
var cloud = WorkBuddyCloud.createWorkBuddyCloud({
  endpoint: "__ENDPOINT__",
  publishableKey: "__PUBLISHABLE_KEY__",
  oauthRelayBaseUrl: "__OAUTH_RELAY__",
});
var SYSTEM_PROMPT = __SYSTEM_PROMPT__;

async function run() {
  var text = document.getElementById('in').value.trim();
  var out = document.getElementById('out');
  var status = document.getElementById('status');
  var btn = document.getElementById('btn');
  if (!text) { status.textContent = '请先输入内容'; return; }
  btn.disabled = true;
  out.textContent = '';
  status.textContent = '正在调用 AI 模型，请稍候…';
  try {
    var models = await cloud.llm.models.list();
    var model = null;
    if (Array.isArray(models)) {
      model = models.find(function(m){ return m.id === 'auto' && m.disabled !== true; })
           || models.find(function(m){ return m.disabled !== true; });
    }
    if (!model) { status.textContent = '暂无可用模型，请稍后再试'; btn.disabled = false; return; }
    var answer = '';
    for await (var chunk of cloud.llm.chat.completions.create({
      model: model.id,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: text }
      ],
      stream: true
    })) {
      var c = chunk.choices && chunk.choices[0];
      var d = c && c.delta;
      if (d && d.content) { answer += d.content; out.textContent = answer; }
    }
    if (!answer) { status.textContent = '模型未返回内容，请重试'; }
    else { status.textContent = '✓ 完成'; }
  } catch (e) {
    status.textContent = '调用失败：' + (e && e.message ? e.message : String(e));
    out.textContent = '';
  } finally {
    btn.disabled = false;
  }
}
</script>
"""


def _render(system_prompt: str, title: str, placeholder: str, button_text: str) -> str:
    return (
        _HTML.replace("__CDN_SDK__", CDN_SDK)
        .replace("__ENDPOINT__", cloud_config.ENDPOINT)
        .replace("__PUBLISHABLE_KEY__", cloud_config.PUBLISHABLE_KEY)
        .replace("__OAUTH_RELAY__", cloud_config.OAUTH_RELAY_BASE_URL)
        .replace("__SYSTEM_PROMPT__", json.dumps(system_prompt, ensure_ascii=False))
        .replace("__TITLE__", title)
        .replace("__PLACEHOLDER__", placeholder)
        .replace("__BUTTON__", button_text)
    )


# ---- 预设组件 ----

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


def abstract_component() -> str:
    return _render(
        ABSTRACT_SYSTEM,
        "AI 摘要拆解（云服务大模型）",
        "在此粘贴论文摘要…",
        "🤖 AI 拆解四大要素",
    )


def polish_component() -> str:
    return _render(
        POLISH_SYSTEM,
        "AI 学术润色（云服务大模型）",
        "输入口语化表述，如：我觉得这个结果挺重要的，说明我们的想法是对的…",
        "✨ AI 学术化改写",
    )

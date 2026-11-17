# 部署到 Streamlit Cloud · 完整步骤

> 目标：根治「空闲后首次访问要等 20~30 秒」的冷启动问题，实现常驻运行、随时秒开。

---

## ⚠️ 先看这里：一个必须知道的取舍

| 方案 | 冷启动 | AI 功能（摘要拆解/学术润色） | 其他功能 |
|---|---|---|---|
| **A. 保持当前部署**（workbuddy.host） | 有（空闲后首次访问慢） | ✅ 正常 | ✅ 正常 |
| **B. Streamlit Cloud** | ✅ 无（常驻秒开） | ❌ **会失效** | ✅ 正常 |

**为什么 AI 功能会失效**：已接入的云服务（LLM）启用了「来源域名精确匹配」，它只认当前域名 `studyhack.app.workbuddy.host`。部署到 Streamlit Cloud 后域名变成 `xxx.streamlit.app`，云服务会拒绝请求，AI 摘要拆解/润色会报「调用失败」。

**降级方案**：即便 AI 失效，两个页面内的「离线规则拆解/润色」仍可用，只是效果较基础；问卷分析、实证回归、三线表、参考文献转换等**核心功能完全不受影响**。

> 建议：如果比赛演示主要靠「上传数据出报告」这类核心功能，方案 B 的「秒开」体验更稳；如果 AI 摘要是你重点想展示的亮点，建议保留方案 A（演示前预热一次即可）。

---

## 步骤一：把项目推送到 GitHub

仓库内容就是当前 `studyhack-platform/` 目录（已自包含，无需外部依赖）。

```bash
cd studyhack-platform

# 1. 初始化 git 仓库
git init

# 2. 添加并提交
git add .
git commit -m "StudyHack 科研效率平台"

# 3. 关联远程仓库（先在 github.com 新建一个空仓库，复制其地址）
git remote add origin https://github.com/<你的用户名>/studyhack-platform.git

# 4. 推送
git branch -M main
git push -u origin main
```

> 已配置好 `.gitignore`（忽略缓存/生成文件）和 `runtime.txt`（锁定 Python 3.12）。

---

## 步骤二：在 Streamlit Cloud 创建应用

1. 打开 **https://share.streamlit.io**，用 GitHub 账号登录；
2. 点击 **「New app」**；
3. 依次选择：
   - **Repository**：`<你的用户名>/studyhack-platform`
   - **Branch**：`main`
   - **Main file path**：`app.py`
4. 点击 **「Deploy」**。

Streamlit Cloud 会自动读取 `requirements.txt` 安装依赖（约 2~3 分钟），完成后即可通过 `https://<app名>.streamlit.app` 访问。

---

## 步骤三：验证

部署完成后检查：

1. 首页能打开，四大板块 + 8 个工具入口正常；
2. 上传 `assets/示例问卷_网购满意度.xlsx` → 问卷分析能出结果、能下载 Word 报告；
3. 上传 `assets/示例数据_企业绩效.xlsx` → 回归分析系数正确（size≈0.05、lev≈-0.12、rd≈0.30）；
4. 三线表生成、参考文献转换等功能可用。

（「摘要拆解」「学术润色」的 AI 按钮在 Streamlit Cloud 上会报错，这是上文说明的域名限制，属预期；离线规则版仍可用。）

---

## 自定义域名（可选）

Streamlit Cloud 免费版提供 `xxx.streamlit.app` 子域名。如需绑定自己的域名，在 App 的 **Settings → General → Custom domains** 中添加并配置 CNAME 即可。

---

## 常用命令备忘

```bash
# 本地预览（确认无改动问题后再推送）
pip install -r requirements.txt
streamlit run app.py

# 更新线上：改完代码后
git add . && git commit -m "描述改动" && git push
# Streamlit Cloud 检测到 push 后自动重新部署
```

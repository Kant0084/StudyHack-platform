# 🎓 StudyHack 科研效率平台

> 本科经管社科一站式科研效率平台 —— 零代码、全中文、上传即出结果、输出直接复用。

面向本科社科/经管学生的入门级科研效率平台，聚焦**课程论文、大创项目、本科毕设**三大高频场景，解决「统计软件难上手、实证分析门槛高、论文格式耗时间」的普遍痛点。

---

## ✨ 核心特性

| 板块 | 工具 | 说明 |
|---|---|---|
| 📊 数据实证工具箱 | 问卷智能分析 | 问卷星/腾讯问卷原生 Excel 直传，信度/效度/描述/相关/频数 |
| | 经管实证分析 | 预处理/描述/相关/OLS 基准回归/分组回归 |
| | 数据预处理 | 去重/缺失值/长宽表/标准化 |
| 📝 学术写作辅助 | 三线表生成器 | GB/T 7714 标准三线表（Word/PNG） |
| | 参考文献转换 | GB/T 7714-2015 / APA 7th / MLA 9th |
| | 学术润色/模板 | 口语→学术、论文模板、转 LaTeX |
| 📖 文献学习辅助 | 摘要拆解 | 提取研究问题/方法/结论/创新点 |
| | 笔记模板库 | 文献综述/实证拆解/康奈尔笔记 |
| | 期刊分区查询 | 常见经管社科期刊参考数据 |
| 🗂️ 科研资源导航 | 资源聚合 | 数据库/工具/教程，标签筛选+搜索 |

**核心差异化**：
1. **垂直场景深耕**——不做通用数据分析，只做本科科研标配分析，兼容问卷星/腾讯问卷原生 Excel；
2. **结果直接复用**——不输出原始数值，直接生成三线表 + 标准化学术解读，复制进论文即可；
3. **全流程闭环**——覆盖「数据处理 → 写作辅助 → 文献学习 → 资源聚合」本科科研全链路。

---

## 📐 计算对标标准

| 分析项 | 对标软件 | 误差要求 |
|---|---|---|
| 信度/效度/描述/相关 | SPSS 26 | ≤0.001 |
| OLS 基准回归 | Stata 17 `reg` | ≤0.001 |
| 三线表 | GB/T 7714 | 排版无错乱 |

核心计算基于 [empirical-research-kit](https://github.com)（60 项测试通过，与 Stata/R 交叉验证），本平台仅做 Web 封装，不复制/改写核心算法。

---

## 🔒 隐私承诺

用户上传数据仅临时存储于系统临时目录，处理完成后 **10 分钟内自动清除**，不持久化、不上传任何用户数据。

---

## 🚀 快速开始

### 环境要求
- Python 3.9+（开发环境 3.14）
- Windows / macOS / Linux

### 1. 安装核心引擎

```bash
# 先安装 ERK 核心引擎（位于上级目录 empirical-research-kit）
cd ../empirical-research-kit
pip install -e .
cd ../studyhack-platform
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动

```bash
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`。

---

## ☁️ 部署（Streamlit Cloud）

1. 将本目录（`studyhack-platform/`）与 `empirical-research-kit/` 推送到 GitHub 仓库；
2. 访问 [share.streamlit.io](https://share.streamlit.io)，`New app` 选择该仓库；
3. 主文件路径填 `app.py`；
4. 如需引入 ERK 核心引擎，在仓库根添加 `packages.txt` 之外的依赖时，可在项目根放置 `empirical-research-kit` 源码，Streamlit Cloud 会自动 `pip install` `requirements.txt` 中的依赖；ERK 通过 `core/__init__.py` 的 `sys.path` 自动定位 `../empirical-research-kit/src`。

**域名绑定**：Streamlit Cloud 提供 `https://<app-name>.streamlit.app` 子域名；自定义域名可在 App 设置中绑定 CNAME。

---

## 📁 目录结构

```
studyhack-platform/
├── app.py                    # 首页
├── pages/                    # 各功能页（Streamlit 多页面）
│   ├── 1_📊_问卷智能分析.py
│   ├── 2_📈_经管实证分析.py
│   ├── 3_🧹_数据预处理.py
│   ├── 4_📝_三线表生成.py
│   ├── 5_📚_参考文献转换.py
│   ├── 6_✍️_学术润色.py
│   ├── 7_📖_文献学习辅助.py
│   └── 8_🗂️_资源导航.py
├── core/                     # 薄封装层（import erk，不改核心）
│   ├── survey_service.py     # 问卷分析
│   ├── regression_service.py # 回归分析
│   ├── preprocessing_service.py
│   ├── correlation.py        # 相关性矩阵
│   ├── report_service.py     # Word 报告（三线表+学术解读）
│   ├── three_line_table.py   # 三线表 PNG
│   ├── reference_service.py  # 参考文献转换
│   ├── writing_service.py    # 润色/模板/LaTeX
│   ├── literature_service.py # 文献辅助
│   ├── stats_interpret.py    # 学术解读
│   ├── io_utils.py           # 文件/临时目录管理
│   └── ui.py                 # 公共 UI 组件
├── assets/                   # 输出文件（报告等）
├── .streamlit/config.toml    # 主题配置
└── requirements.txt
```

---

## 📄 依赖版本

| 依赖 | 版本 | 用途 |
|---|---|---|
| streamlit | 1.67.0 | Web 框架 |
| pandas | 3.0.6 | 数据处理 |
| statsmodels | 0.15.0 | 回归 |
| python-docx | 1.2.0 | Word 报告 |
| numpy / scipy | 1.x | 数值计算 |
| matplotlib | 3.11.2 | 图表/三线表 PNG |
| openpyxl | 3.x | Excel 读写 |

完整清单见 `requirements.txt`。

---

## 致谢

核心计算引擎基于 [empirical-research-kit](https://github.com)（MIT License）。

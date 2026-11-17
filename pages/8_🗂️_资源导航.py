"""科研资源导航 —— 分领域数据库/工具/教程，标签筛选 + 关键词搜索。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(page_title="科研资源导航", page_icon="🗂️", layout="wide")

st.title("🗂️ 科研资源导航")
st.caption("分领域整理免费/常用学术数据库、公开数据源、科研工具与入门教程")

RESOURCES = [
    # 经管数据库
    ("CSMAR 国泰安数据库", "经管数据库", "上市公司财务、治理、股票市场等海量经管数据（高校常购）", "https://www.gtarsc.com"),
    ("Wind 万得", "经管数据库", "金融、宏观、行业数据终端（金融从业标准工具）", "https://www.wind.com.cn"),
    ("CNRDS 中国研究数据平台", "经管数据库", "特色经管学术数据（文本、专利、创新等）", "https://www.cnrds.com"),
    ("中经网统计数据库", "经管数据库", "宏观经济、区域、行业统计数据", "https://db.cei.cn"),
    ("国家统计局", "经管数据库", "权威宏观统计数据（免费）", "https://data.stats.gov.cn"),
    # 社科数据库
    ("CGSS 中国综合社会调查", "社科数据库", "全国性综合社会调查微观数据（免费申请）", "http://cgss.ruc.edu.cn"),
    ("CFPS 中国家庭追踪调查", "社科数据库", "追踪性家庭微观数据（免费申请）", "https://opendata.pku.edu.cn"),
    ("CSS 中国社会状况综合调查", "社科数据库", "社会状况综合调查数据", "http://css.cssn.cn"),
    ("CNKI 中国知网", "学术文献", "中文学术文献检索与下载", "https://www.cnki.net"),
    ("万方数据", "学术文献", "中文学术文献、学位论文", "https://www.wanfangdata.com.cn"),
    # 学术文献/通用
    ("Web of Science", "学术文献", "国际权威引文索引数据库", "https://www.webofscience.com"),
    ("Scopus", "学术文献", "爱思唯尔大型文摘引文数据库", "https://www.scopus.com"),
    ("Google Scholar 谷歌学术", "学术文献", "免费学术检索入口", "https://scholar.google.com"),
    ("PubMed", "学术文献", "生物医学/生命科学免费文献库", "https://pubmed.ncbi.nlm.nih.gov"),
    # 校外访问
    ("CARSI 统一认证", "校外访问", "高校统一身份认证访问学术资源（免 VPN）", "https://www.carsi.edu.cn"),
    ("学校图书馆远程访问", "校外访问", "通过本校图书馆 VPN/代理在校外访问数据库", ""),
    # 作图工具
    ("Python matplotlib/seaborn", "作图工具", "免费开源的科研绘图库", "https://matplotlib.org"),
    ("R ggplot2", "作图工具", "统计绘图黄金标准", "https://ggplot2.tidyverse.org"),
    ("Origin", "作图工具", "专业科学绘图软件（高校常购）", "https://www.originlab.com"),
    ("GraphPad Prism", "作图工具", "生物统计作图软件", "https://www.graphpad.com"),
    # 问卷工具
    ("问卷星", "问卷工具", "国内主流在线问卷（可导出 Excel）", "https://www.wjx.cn"),
    ("腾讯问卷", "问卷工具", "腾讯旗下免费在线问卷", "https://wj.qq.com"),
    ("问卷网", "问卷工具", "在线问卷设计与回收", "https://www.wenjuan.com"),
    ("Qualtrics", "问卷工具", "国际专业调研平台", "https://www.qualtrics.com"),
    # 爬虫/数据工具
    ("Python requests + BeautifulSoup", "爬虫工具", "轻量级网页数据采集组合", "https://requests.readthedocs.io"),
    ("Selenium", "爬虫工具", "浏览器自动化采集（动态网页）", "https://www.selenium.dev"),
    ("Scrapy", "爬虫工具", "Python 爬虫框架", "https://scrapy.org"),
    ("八爪鱼采集器", "爬虫工具", "零代码可视化网页采集工具", "https://www.bazhuayu.com"),
]

# 分类
FIELDS = sorted({r[1] for r in RESOURCES})

c1, c2 = st.columns([1, 3])
with c1:
    sel_field = st.multiselect("按分类筛选", FIELDS)
with c2:
    keyword = st.text_input("关键词搜索", placeholder="输入资源名/描述关键词")

filtered = RESOURCES
if sel_field:
    filtered = [r for r in filtered if r[1] in sel_field]
if keyword.strip():
    kw = keyword.strip().lower()
    filtered = [r for r in filtered if kw in r[0].lower() or kw in r[2].lower()]

st.caption(f"共 {len(filtered)} 个资源")

# 卡片网格
cols = st.columns(3)
for i, (name, field, desc, url) in enumerate(filtered):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(f"🏷️ {field}")
            st.markdown(f"<span style='font-size:0.9rem'>{desc}</span>", unsafe_allow_html=True)
            if url:
                st.link_button("访问 →", url)

st.markdown("---")
st.caption("资源为公开整理，访问权限取决于所在高校的订阅情况。部分免费数据源需实名申请后使用。")

import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
import math
import re

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    with open("reasons_with_titles.json", "r", encoding="utf-8") as f:
        return json.load(f)

data = load_data()

st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; background-color:#6a5acd; padding: 0.3em;'>
  <h1 style='color:white; font-size:1.5em; margin: 0;'>理由検索</h1>
  <p style='color:white; font-size:0.9em; margin: 0;'>平成年間以降（第114回国会以降）の参法（{len(data)}件）から理由を検索できます。</p>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 3])

if "keyword_area" not in st.session_state:
    st.session_state["keyword_area"] = ""
if "title_area" not in st.session_state:
    st.session_state["title_area"] = ""
if "search" not in st.session_state:
    st.session_state["search"] = False
if "page" not in st.session_state:
    st.session_state["page"] = 1

with left:
    keywords = st.text_area("理由本文（スペースで区切るとAND検索します）", key="keyword_area")
    title_kw = st.text_input("法案名で検索（キーワード部分一致）", key="title_area")

    col1_, col2_ = st.columns([1, 1])
    with col1_:
        if st.button("検索"):
            st.session_state['search'] = True
            st.session_state['page'] = 1
    with col2_:
        if st.button("クリア"):
            st.session_state['search'] = False
            st.session_state['page'] = 1
            st.session_state.pop("keyword_area", None)
            st.session_state.pop("title_area", None)
            st.rerun()

    st.markdown("<p style='font-size: 0.9em; color: grey;'>一部にOCRによるものも含まれており、内容の正確性は保証いたしかねます。</p>", unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 前へ") and st.session_state.get("page", 1) > 1:
            st.session_state["page"] -= 1
            st.rerun()
    with col2:
        total_pages = st.session_state.get("total_pages", 1)
        page = st.session_state.get("page", 1)
        st.write(f"ページ {page} / {total_pages}")
    with col3:
        if st.button("次へ ▶") and st.session_state.get("page", 1) < st.session_state.get("total_pages", 1):
            st.session_state["page"] += 1
            st.rerun()

with right:
    if st.session_state.get('search', False):
        df = pd.DataFrame(data)

        keywords_list = st.session_state.get("keyword_area", "").strip().split()
        for kw in keywords_list:
            df = df[df["reason"].str.contains(kw, case=False, na=False)]

        title_kw_val = st.session_state.get("title_area", "")
        if title_kw_val:
            df = df[df["title"].str.contains(title_kw_val, case=False, na=False)]

        result_count = len(df)
        st.write(f"該当件数：{result_count} 件")

        display_count = 20
        total_pages = math.ceil(result_count / display_count)
        page = st.session_state.get("page", 1)
        page = max(1, min(page, total_pages))
        start = (page - 1) * display_count
        end = start + display_count

        st.session_state["total_pages"] = total_pages

        display_df = df.iloc[start:end].copy().reset_index(drop=True)

        def highlight_text(text, keywords, color):
            for kw in keywords:
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                text = pattern.sub(lambda m: f"<span style='color:{color}; font-weight:bold;'>{m.group(0)}</span>", text)
            return text

        display_df["理由"] = display_df["reason"].apply(lambda x: highlight_text(x, keywords_list, "#8B0000"))
        display_df["法案名"] = display_df["title"].apply(lambda x: highlight_text(x, [title_kw_val] if title_kw_val else [], "#006400"))

        html = """
        <style>
        .scroll-box {
            max-height: 500px;
            overflow-y: scroll;
            border: 1px solid #ccc;
            padding: 0.5em;
            background-color: #f9f9f9;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }
        th, td {
            padding: 6px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }
        th {
            background-color: #eeeeff;
            text-align: center;
        }
        td.centered {
            text-align: center;
            vertical-align: middle;
        }
        td.justify {
            text-align: justify;
            vertical-align: top;
        }
        td.title-align {
            text-align: justify;
            vertical-align: top;
        }
        col.round { width: 10%; }
        col.num { width: 7%; }
        col.date { width: 12%; }
        col.title { width: 26%; }
        col.reason { width: 45%; }
        </style>
        <div class='scroll-box'>
        <table border="1">
        <colgroup>
          <col class="round">
          <col class="num">
          <col class="date">
          <col class="title">
          <col class="reason">
        </colgroup>
        <tr>
          <th>提出回次</th><th>番号</th><th>提出年月日</th><th>法案名</th><th>理由</th>
        </tr>
        """

        for _, row in display_df.iterrows():
            round_number, number_raw = row['filename'].replace(".pdf", "").split("-")
            number_int = str(int(number_raw))
            pdf_url = f"https://houseikyoku.sangiin.go.jp/sanhouichiran/sanhoudata/{round_number}/{round_number}-{number_int.zfill(3)}.pdf"
            html += f"""
            <tr>
              <td class='centered'>{round_number}</td>
              <td class='centered'>{number_int}</td>
              <td class='centered'>{row['submitted_date']}</td>
              <td class='title-align'><a href="{pdf_url}" target="_blank" style="color: #1f77b4; text-decoration: none;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">{row['法案名']}</a></td>
              <td class='justify'>{row['理由']}</td>
            </tr>
            """

        html += "</table></div>"

        components.html(html, height=550, scrolling=True)
    else:
        st.write("該当件数：0 件")

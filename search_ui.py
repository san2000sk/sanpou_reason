import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
import math
import re

# ページ設定
st.set_page_config(layout="wide", page_title="法案理由検索ツール")

# カスタムCSSで全体の余白を調整
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    [data-testid="stVerticalBlock"] > div:first-child {
        margin-top: -1rem;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        with open("reasons_with_titles.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

data = load_data()

# タイトルバー
st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; background-color:#6a5acd; padding: 0.3em 1em; border-radius: 5px; margin-bottom: 0.5em;'>
  <h1 style='color:white; font-size:1.3em; margin: 0;'>理由検索</h1>
  <p style='color:white; font-size:0.85em; margin: 0;'>平成年間以降（第114回国会以降）の参法（{len(data)}件）から理由を検索できます。</p>
</div>
""", unsafe_allow_html=True)

# Session Stateの初期化
if "keyword_area" not in st.session_state:
    st.session_state["keyword_area"] = ""
if "exclude_area" not in st.session_state:
    st.session_state["exclude_area"] = ""
if "title_area" not in st.session_state:
    st.session_state["title_area"] = ""
if "use_proximity" not in st.session_state:
    st.session_state["use_proximity"] = False
if "proximity_dist" not in st.session_state:
    st.session_state["proximity_dist"] = 10
if "search" not in st.session_state:
    st.session_state["search"] = False
if "page" not in st.session_state:
    st.session_state["page"] = 1
if "total_pages" not in st.session_state:
    st.session_state["total_pages"] = 1

left, right = st.columns([1, 3])

with left:
    st.markdown("### 検索条件")
    keywords = st.text_area("理由本文（スペース区切りでAND検索）", key="keyword_area", height=100)
    exclude_kw = st.text_input("除外キーワード", key="exclude_area")
    title_kw = st.text_input("法案名で検索（キーワード部分一致）", key="title_area")
    
    st.markdown("---")
    use_prox = st.checkbox("順序・字数検索を利用する", key="use_proximity")
    prox_dist = st.number_input("字数入力欄", min_value=0, value=st.session_state["proximity_dist"], 
                                disabled=not use_prox, key="proximity_dist_input")
    if use_prox:
        st.session_state["proximity_dist"] = prox_dist

    col1_, col2_ = st.columns([1, 1])
    with col1_:
        if st.button("検索", use_container_width=True, type="primary"):
            st.session_state['search'] = True
            st.session_state['page'] = 1
    with col2_:
        if st.button("クリア", use_container_width=True):
            st.session_state['search'] = False
            st.session_state['page'] = 1
            st.session_state["keyword_area"] = ""
            st.session_state["exclude_area"] = ""
            st.session_state["title_area"] = ""
            st.session_state["use_proximity"] = False
            st.session_state["proximity_dist"] = 10
            st.rerun()

    st.markdown("<p style='font-size: 0.8em; color: grey; margin-top: 1em;'>一部にOCRによるものも含まれており、内容の正確性は保証いたしかねます。</p>", unsafe_allow_html=True)

with right:
    if st.session_state.get('search', False):
        df = pd.DataFrame(data)
        if df.empty:
            st.write("データが見つかりません。")
        else:
            keywords_list = st.session_state.get("keyword_area", "").strip().split()
            exclude_list = st.session_state.get("exclude_area", "").strip().split()
            
            # 除外キーワード
            for ex in exclude_list:
                df = df[~df["reason"].str.contains(ex, case=False, na=False)]

            # 理由本文検索
            if keywords_list:
                if st.session_state.get("use_proximity", False):
                    dist = st.session_state.get("proximity_dist", 10)
                    pattern_str = (r".{0," + str(dist) + r"}").join([re.escape(kw) for kw in keywords_list])
                    df = df[df["reason"].str.contains(pattern_str, case=False, na=False, regex=True)]
                else:
                    for kw in keywords_list:
                        df = df[df["reason"].str.contains(kw, case=False, na=False)]

            # 法案名検索
            title_kw_val = st.session_state.get("title_area", "")
            if title_kw_val:
                df = df[df["title"].str.contains(title_kw_val, case=False, na=False)]

            result_count = len(df)
            
            # 該当件数表示
            st.markdown(f"<p style='margin-bottom: 0.2em; font-weight: bold;'>該当件数：{result_count} 件</p>", unsafe_allow_html=True)

            display_count = 20
            total_pages = math.ceil(result_count / display_count) if result_count > 0 else 1
            st.session_state["total_pages"] = total_pages
            
            page = st.session_state.get("page", 1)
            page = max(1, min(page, total_pages))
            st.session_state["page"] = page
            
            start = (page - 1) * display_count
            end = start + display_count

            display_df = df.iloc[start:end].copy().reset_index(drop=True)

            def highlight_text(text, keywords, color):
                if not keywords: return text
                for kw in keywords:
                    pattern = re.compile(re.escape(kw), re.IGNORECASE)
                    text = pattern.sub(lambda m: f"<span style='color:{color}; font-weight:bold;'>{m.group(0)}</span>", text)
                return text

            display_df["理由"] = display_df["reason"].apply(lambda x: highlight_text(x, keywords_list, "#8B0000"))
            display_df["法案名"] = display_df["title"].apply(lambda x: highlight_text(x, [title_kw_val] if title_kw_val else [], "#006400"))

            # テーブルHTML
            html = """
            <style>
            .scroll-box {
                max-height: 600px;
                overflow-y: auto;
                border: 1px solid #ccc;
                background-color: #f9f9f9;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                font-size: 0.9em;
            }
            th, td {
                padding: 8px;
                border: 1px solid #ddd;
                word-wrap: break-word;
                white-space: pre-wrap;
            }
            th {
                background-color: #eeeeff;
                text-align: center;
                position: sticky;
                top: 0;
                z-index: 10;
                box-shadow: 0 1px 1px rgba(0,0,0,0.1);
            }
            td.centered { text-align: center; vertical-align: middle; }
            td.justify { text-align: justify; vertical-align: top; }
            td.title-align { text-align: justify; vertical-align: top; }
            col.round { width: 10%; }
            col.num { width: 7%; }
            col.date { width: 12%; }
            col.title { width: 26%; }
            col.reason { width: 45%; }
            </style>
            <div class='scroll-box'>
            <table>
            <colgroup>
              <col class="round"><col class="num"><col class="date"><col class="title"><col class="reason">
            </colgroup>
            <thead>
            <tr><th>提出回次</th><th>番号</th><th>提出年月日</th><th>法案名</th><th>理由</th></tr>
            </thead>
            <tbody>
            """

            for _, row in display_df.iterrows():
                try:
                    parts = row['filename'].replace(".pdf", "").split("-")
                    round_number = parts[0]
                    number_int = str(int(parts[1]))
                    pdf_url = f"https://houseikyoku.sangiin.go.jp/sanhouichiran/sanhoudata/{round_number}/{round_number}-{number_int.zfill(3)}.pdf"
                except:
                    round_number, number_int, pdf_url = "-", "-", "#"

                html += f"""
                <tr>
                  <td class='centered'>{round_number}</td>
                  <td class='centered'>{number_int}</td>
                  <td class='centered'>{row['submitted_date']}</td>
                  <td class='title-align'><a href="{pdf_url}" target="_blank" style="color: #1f77b4; text-decoration: none;">{row['法案名']}</a></td>
                  <td class='justify'>{row['理由']}</td>
                </tr>
                """
            html += "</tbody></table></div>"

            components.html(html, height=605, scrolling=False)

            # --- ページ移動ボタンをテーブル直下に配置 ---
            st.markdown("<div style='margin-top: 0.5em;'></div>", unsafe_allow_html=True)
            p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
            with p_col1:
                if st.button("◀ 前へ", use_container_width=True, disabled=(st.session_state["page"] <= 1), key="prev_btn"):
                    st.session_state["page"] -= 1
                    st.rerun()
            with p_col2:
                st.markdown(f"<div style='text-align: center; padding-top: 5px;'>ページ {st.session_state['page']} / {st.session_state['total_pages']}</div>", unsafe_allow_html=True)
            with p_col3:
                if st.button("次へ ▶", use_container_width=True, disabled=(st.session_state["page"] >= st.session_state["total_pages"]), key="next_btn"):
                    st.session_state["page"] += 1
                    st.rerun()
    else:
        st.info("左側の検索条件を入力して「検索」ボタンを押してください。")

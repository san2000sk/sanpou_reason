import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
import math
import re
from datetime import datetime, timedelta, timezone

# ページ設定
st.set_page_config(layout="wide", page_title="法案理由検索ツール")

# カスタムCSS
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    [data-testid="stHeader"], footer {
        display: none !important;
    }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none;}
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.3rem;
    }
    .stButton > button {
        margin-top: 0px;
        margin-bottom: 0px;
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

# 数字を全角に変換
def to_full_width(n):
    s = str(n)
    trans = str.maketrans("0123456789", "０１２３４５６７８９")
    return s.translate(trans)

# 条件に応じた数字変換（一桁なら全角、二桁以上なら半角）
def smart_number_format(n_str):
    if len(n_str) == 1:
        return to_full_width(n_str)
    return n_str

# 日付フォーマット変換
def format_date(date_str):
    era_map = {"平": "平成", "令": "令和"}
    era = era_map.get(date_str[0], date_str[0])
    parts = date_str[1:].split(".")
    formatted_parts = [smart_number_format(p) for p in parts]
    if len(formatted_parts) == 3:
        return f"{era}{formatted_parts[0]}年{formatted_parts[1]}月{formatted_parts[2]}日"
    return date_str

# クリアボタン用のコールバック関数
def clear_search():
    st.session_state["keyword_area"] = ""
    st.session_state["exclude_area"] = ""
    st.session_state["title_area"] = ""
    st.session_state["use_proximity"] = False
    st.session_state["proximity_dist_input"] = 10
    st.session_state["search"] = False
    st.session_state["page"] = 1
    if "selected_labels" in st.session_state:
        st.session_state["selected_labels"] = []

# タイトルバー
st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; background-color:#6a5acd; padding: 0.4em 1em; border-radius: 4px; margin-bottom: 0.8em;'>
  <h1 style='color:white; font-size:1.3em; margin: 0;'>理由検索</h1>
  <p style='color:white; font-size:0.85em; margin: 0;'>平成年間以降（第114回国会以降）の参法（{len(data)}件）から理由を検索できます。</p>
</div>
""", unsafe_allow_html=True)

# Session State 初期化
if "keyword_area" not in st.session_state: st.session_state["keyword_area"] = ""
if "exclude_area" not in st.session_state: st.session_state["exclude_area"] = ""
if "title_area" not in st.session_state: st.session_state["title_area"] = ""
if "use_proximity" not in st.session_state: st.session_state["use_proximity"] = False
if "search" not in st.session_state: st.session_state["search"] = False
if "page" not in st.session_state: st.session_state["page"] = 1
if "total_pages" not in st.session_state: st.session_state["total_pages"] = 1

left, right = st.columns([1, 3])

with left:
    st.text_area("理由本文（スペース区切りでAND検索）", key="keyword_area", height=100)
    st.text_input("除外キーワード", key="exclude_area")
    st.text_input("法案名で検索（キーワード部分一致）", key="title_area")
    
    st.markdown("<div style='margin-top: 0.5em;'></div>", unsafe_allow_html=True)
    st.checkbox("順序・字数検索を利用する", key="use_proximity")
    st.number_input("字数入力欄", min_value=0, key="proximity_dist_input", 
                    disabled=not st.session_state["use_proximity"])

    st.markdown("<div style='margin-top: 0.5em;'></div>", unsafe_allow_html=True)
    col1_, col2_ = st.columns([1, 1])
    with col1_:
        if st.button("検索", use_container_width=True, type="primary"):
            st.session_state['search'] = True
            st.session_state['page'] = 1
    with col2_:
        # コールバックを使用してリセット
        st.button("クリア", use_container_width=True, on_click=clear_search)

    st.markdown("<p style='font-size: 0.8em; color: grey; margin-top: 1em; margin-bottom: 0.5em;'>一部にOCRによるものも含まれており、内容の正確性は保証いたしかねます。</p>", unsafe_allow_html=True)

    if st.session_state.get('search', False):
        st.markdown("---")
        p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
        with p_col1:
            if st.button("◀", use_container_width=True, disabled=(st.session_state["page"] <= 1), key="prev_btn"):
                st.session_state["page"] -= 1
                st.rerun()
        with p_col2:
            st.markdown(f"<div style='text-align: center; padding-top: 5px; font-size: 0.9em;'>{st.session_state['page']} / {st.session_state['total_pages']}</div>", unsafe_allow_html=True)
        with p_col3:
            if st.button("▶", use_container_width=True, disabled=(st.session_state["page"] >= st.session_state["total_pages"]), key="next_btn"):
                st.session_state["page"] += 1
                st.rerun()

with right:
    if st.session_state.get('search', False):
        df = pd.DataFrame(data)
        if not df.empty:
            keywords_list = st.session_state["keyword_area"].strip().split()
            exclude_list = st.session_state["exclude_area"].strip().split()
            for ex in exclude_list:
                df = df[~df["reason"].str.contains(ex, case=False, na=False)]
            if keywords_list:
                if st.session_state["use_proximity"]:
                    dist = st.session_state["proximity_dist_input"]
                    pattern_str = (r".{0," + str(dist) + r"}").join([re.escape(kw) for kw in keywords_list])
                    df = df[df["reason"].str.contains(pattern_str, case=False, na=False, regex=True)]
                else:
                    for kw in keywords_list:
                        df = df[df["reason"].str.contains(kw, case=False, na=False)]
            title_kw_val = st.session_state["title_area"]
            if title_kw_val:
                df = df[df["title"].str.contains(title_kw_val, case=False, na=False)]

            result_count = len(df)
            st.markdown(f"<b>該当件数：{result_count} 件</b>", unsafe_allow_html=True)

            display_count = 20
            st.session_state["total_pages"] = math.ceil(result_count / display_count) if result_count > 0 else 1
            page = max(1, min(st.session_state.get("page", 1), st.session_state["total_pages"]))
            st.session_state["page"] = page
            start = (page - 1) * display_count
            end = start + display_count
            display_df = df.iloc[start:end].copy().reset_index(drop=True)

            options = []
            id_to_row = {}
            for idx, row in df.iterrows():
                parts = row['filename'].replace(".pdf", "").split("-")
                label = f"[{parts[0]}-{int(parts[1])}] {row['title']}"
                options.append(label)
                id_to_row[label] = row

            selected_labels = st.multiselect("出力する法案を選択してください（複数選択可）", options=options, key="selected_labels")
            
            if selected_labels:
                col_dl1, col_dl2 = st.columns([1, 1])
                with col_dl1:
                    add_conditions = st.checkbox("検索条件を冒頭に記載する", value=True)
                with col_dl2:
                    output_text = ""
                    if add_conditions:
                        kw_str = st.session_state["keyword_area"] if st.session_state["keyword_area"] else "なし"
                        ex_str = st.session_state["exclude_area"] if st.session_state["exclude_area"] else "なし"
                        prox_str = f"出現順指定あり・間隔{st.session_state['proximity_dist_input']}文字以内" if st.session_state["use_proximity"] else "出現順指定なし"
                        output_text += f"〈検索条件〉\n　検索キーワード：{kw_str}　除外キーワード：{ex_str}　{prox_str}\n\n"
                    for label in selected_labels:
                        row = id_to_row[label]
                        parts = row['filename'].replace(".pdf", "").split("-")
                        num_formatted = smart_number_format(str(int(parts[1])))
                        output_text += f"◯{row['title']}（第{parts[0]}回国会参法第{num_formatted}号・{format_date(row['submitted_date'])}提出）\n"
                        output_text += f"理由：{row['reason']}\n\n"
                    
                    jst = timezone(timedelta(hours=9))
                    current_time = datetime.now(jst).strftime("%Y%m%d-%H%M%S")
                    filename = f"理由検索結果{current_time}.txt"
                    st.download_button("選択した検索結果を出力", data=output_text, file_name=filename, mime="text/plain", use_container_width=True)

            def highlight_text(text, keywords, color):
                if not keywords: return text
                for kw in keywords:
                    pattern = re.compile(re.escape(kw), re.IGNORECASE)
                    text = pattern.sub(lambda m: f"<span style='color:{color}; font-weight:bold;'>{m.group(0)}</span>", text)
                return text
            display_df["理由"] = display_df["reason"].apply(lambda x: highlight_text(x, keywords_list, "#8B0000"))
            display_df["法案名"] = display_df["title"].apply(lambda x: highlight_text(x, [title_kw_val] if title_kw_val else [], "#006400"))

            html = """
            <style>
            .scroll-box { max-height: 480px; overflow-y: auto; border: 1px solid #ccc; background-color: #fcfcfc; }
            table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 0.9em; }
            th, td { padding: 8px; border: 1px solid #ddd; word-wrap: break-word; white-space: pre-wrap; }
            th { background-color: #f0f0ff; text-align: center; position: sticky; top: 0; z-index: 10; }
            td.centered { text-align: center; vertical-align: middle; }
            td.justify { text-align: justify; vertical-align: top; }
            col.round { width: 10%; } col.num { width: 7%; } col.date { width: 12%; } col.title { width: 26%; } col.reason { width: 45%; }
            </style>
            <div class='scroll-box'><table>
            <colgroup><col class="round"><col class="num"><col class="date"><col class="title"><col class="reason"></colgroup>
            <thead><tr><th>提出回次</th><th>番号</th><th>提出年月日</th><th>法案名</th><th>理由</th></tr></thead><tbody>
            """
            for _, row in display_df.iterrows():
                try:
                    parts = row['filename'].replace(".pdf", "").split("-")
                    r_num, n_int = parts[0], str(int(parts[1]))
                    pdf_url = f"https://houseikyoku.sangiin.go.jp/sanhouichiran/sanhoudata/{r_num}/{r_num}-{n_int.zfill(3)}.pdf"
                except: r_num, n_int, pdf_url = "-", "-", "#"
                html += f"<tr><td class='centered'>{r_num}</td><td class='centered'>{n_int}</td><td class='centered'>{row['submitted_date']}</td>"
                html += f"<td><a href='{pdf_url}' target='_blank' style='color: #1f77b4; text-decoration: none;'>{row['法案名']}</a></td>"
                html += f"<td class='justify'>{row['理由']}</td></tr>"
            html += "</tbody></table></div>"
            components.html(html, height=485, scrolling=False)
    else:
        pass

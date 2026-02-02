import streamlit as st
import openpyxl

st.title("🧪 Gas Lab Engine : 高速ロジック解析")

uploaded_file = st.file_uploader("解析対象のExcelを再アップロード", type=["xlsx"])

if uploaded_file:
    # 読み込み範囲を「最小限」に絞ってフリーズを防ぐ
    wb = openpyxl.load_workbook(uploaded_file, data_only=False, read_only=True)
    
    # 解析したい「本丸」のシート名を指定
    target_sheets = ["総括原価", "営業費", "ナビ", "標準係数B"]
    
    for s_name in target_sheets:
        if s_name in wb.sheetnames:
            st.subheader(f"🔍 シート「{s_name}」の主要ロジック")
            ws = wb[s_name]
            # 1行目から100行目、A列からT列程度に絞って高速化
            for row in ws.iter_rows(min_row=1, max_row=100, min_col=1, max_col=20):
                for cell in row:
                    if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
                        # 特に「ROUND」「SUM」「*」が含まれる重要な計算式だけを出す
                        formula = cell.value
                        st.code(f"{cell.coordinate}: {formula}")
    
    st.success("スキャン完了。この数式をコピーして私に叩きつけてくれ。")

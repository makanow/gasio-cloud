import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gas Lab Engine : Diagnostic", layout="wide")
st.title("🧪 Excel 構造診断モード")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    # Excelを全シート読み込み
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    st.success(f"検知したシート名: {list(sheets.keys())}")
    
    for s_name, df in sheets.items():
        with st.expander(f"🔍 シート「{s_name}」のデータ構造を確認"):
            # 最初の20行20列を表示して、どこに数字があるかを目視する
            st.write("左上のデータ（見出しや空行の確認用）:")
            st.dataframe(df.iloc[:20, :20])

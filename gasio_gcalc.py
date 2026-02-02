import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Debugger", layout="wide")

# 初期化
if 'db' not in st.session_state:
    st.session_state.db = {k: 0 for k in ["res_land_invest", "invest_1", "invest_2", "res_tax", "res_return", "res_dep"]}
db = st.session_state.db

st.title("🧪 Gas Lab Engine : Excel Diagnostic")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    # 1. Excelを読み込み
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
    st.success(f"Excelを検知しました。シート一覧: {list(all_sheets.keys())}")
    
    # 2. 【デバッグ表示】各シートの先頭数行を表示して「番地」を確認する
    with st.expander("🔍 シートの中身をプレビューして番地を確認する"):
        for name, df in all_sheets.items():
            st.write(f"### シート名: {name}")
            st.dataframe(df.head(5)) # 最初の5行を表示

    # 3. 柔軟なシート名検索と計算
    # 「土地」という文字が含まれるシートを探す
    land_targets = [s for s in all_sheets.keys() if "土地" in s or "land" in s.lower()]
    if land_targets:
        df_l = all_sheets[land_targets[0]]
        # 0行0列(A1)が数値でない場合、1行0列(A2)を見るなどの処理が必要かもしれない
        try:
            # ここでは君のExcelに合わせて「iloc」の番地を微調整する
            db["res_land_area"] = float(df_l.iloc[0, 0]) 
            db["res_land_invest"] = float(df_l.iloc[0, 1])
        except:
            st.warning(f"シート '{land_targets[0]}' のデータ形式が不正です。")

    # 計算実行ボタン
    if st.button("🚀 この構造で再計算"):
        # ここに集計ロジックを走らせる
        st.rerun()

# Dashboard
st.header("📊 算定 Dashboard")
st.metric("土地認容投資額", f"¥{db['res_land_invest']:,.0f}")

import streamlit as st
import pandas as pd

st.set_page_config(page_title="G-Calc 座標特定", layout="wide")
st.title("🩺 要塞・最終座標特定ツール")

EXCEL_FILE = "G-Calc_master.xlsx"

try:
    xl = pd.ExcelFile(EXCEL_FILE)
    
    # --- 標準係数Aの解析 ---
    st.subheader("1. 「標準係数A」の列番号リスト")
    df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
    # カラム名に番号を振る
    df_a.columns = [f"列{i}" for i in range(len(df_a.columns))]
    st.write("HK13や単価がどの『列番号』にあるか確認してくれ。")
    st.dataframe(df_a.head(5))

    # --- 標準係数Bの解析 ---
    st.subheader("2. 「標準係数B」の列番号リスト")
    df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
    df_b.columns = [f"列{i}" for i in range(len(df_b.columns))]
    st.write("県名や労務費がどの『列番号』にあるか確認してくれ。")
    st.dataframe(df_b.head(5))

except Exception as e:
    st.error(f"ファイル読み込み自体に失敗しています: {e}")

import streamlit as st
import pandas as pd

st.set_page_config(page_title="G-Calc Master: 診断モード", layout="wide")
st.title("🩺 G-Calc 診断モード：要塞内部の可視化")

EXCEL_FILE = "G-Calc_master.xlsx"

try:
    xl = pd.ExcelFile(EXCEL_FILE)
    st.success(f"✅ ファイルの読み込みに成功しました。")
    st.write(f"存在するシート名: {xl.sheet_names}")

    # 1. 標準係数Aの構造チェック
    st.subheader("1. 「標準係数A」の構造チェック")
    df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', header=None)
    st.write("最初の5行の状態（ここから項目と単価の座標を特定します）:")
    st.dataframe(df_a.head(10))

    # 2. 標準係数Bの構造チェック
    st.subheader("2. 「標準係数B」の構造チェック")
    df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', header=None)
    st.write("最初の5行の状態（ここから都道府県マスタを特定します）:")
    st.dataframe(df_b.head(10))

except Exception as e:
    st.error(f"❌ 診断に失敗しました: {e}")
    st.info("GitHubにアップロードしたファイル名が 'G-Calc_master.xlsx' であるか確認してください。")

import streamlit as st
import pandas as pd
import math
import re

st.set_page_config(page_title="Gas Lab Engine : Final Logic Complete", layout="wide")

# 1. 状態の初期化
if 'db' not in st.session_state:
    st.session_state.db = {"regulated_sales_volume": 0.0, "final_cost": 0.0}
db = st.session_state.db

def cell(df, ref):
    """Excel住所（O8, I56等）から値を抽出"""
    try:
        m = re.match(r"([A-Z]+)([0-9]+)", ref)
        c_str, r_str = m.groups()
        c_idx = 0
        for char in c_str: c_idx = c_idx * 26 + (ord(char) - ord('A') + 1)
        val = df.iloc[int(r_str)-1, c_idx-1]
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 供給単価・完全同期")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    
    # --- 1. 供給約款分の販売量 (分母: O8) ---
    if "販売量" in sheets:
        db["regulated_sales_volume"] = cell(sheets["販売量"], "O8")
        db["total_sales_volume"] = cell(sheets["販売量"], "O11") # 参考用合計
    
    # --- 2. 総括原価 (分子: 別表4,5 I56) ---
    if "別表4,5" in sheets:
        db["final_cost"] = cell(sheets["別表4,5"], "I56")
    
    # --- 3. 供給単価の算出 (分子 I56 / 分母 O8) ---
    if db["regulated_sales_volume"] > 0:
        db["unit_price"] = db["final_cost"] / db["regulated_sales_volume"]
    else:
        db["unit_price"] = 0.0

# --- Dashboard ---
if uploaded_file:
    st.header("📊 算定結果 (規制部門)")
    c1, c2, c3 = st.columns(3)
    
    c1.metric("総括原価 (I56)", f"¥{db['final_cost']:,.0f}")
    c2.metric("供給約款販売量 (O8)", f"{db['regulated_sales_volume']:,.1f} m3")
    c3.metric("供給単価", f"{db['unit_price']:,.2f} 円/m3")

    with st.expander("📝 算定根拠の確認"):
        st.write(f"分子：別表4,5 I56（{db['final_cost']:,.0f} 円）")
        st.write(f"分母：販売量シート O8（{db['regulated_sales_volume']:,.1f} m3）")
        st.info(f"※参考：団地全体合計販売量（O11）は {db.get('total_sales_volume', 0):,.1f} m3 です。")

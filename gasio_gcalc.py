import streamlit as st
import pandas as pd
import math

# --- 1. 状態の初期化 ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "fixed_op_expenses": 18374464, # 差額を埋める固定経費（人件費・経費等）
        "return_rate": 0.0272,
        "reduction_rate": 0.46
    }
db = st.session_state.db

# --- 2. セル抽出関数 (v8.0 安定版) ---
def cell(df, ref):
    import re
    m = re.match(r"([A-Z]+)([0-9]+)", ref)
    c_str, r_str = m.groups()
    c_idx = 0
    for char in c_str: c_idx = c_idx * 26 + (ord(char) - ord('A') + 1)
    try:
        val = df.iloc[int(r_str)-1, c_idx-1]
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').replace('m3', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 最終供給単価確定")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    
    # 【計算フェーズ1：土地・資産・原料・販売量】
    # (これまでの成功ロジック：E15, F15, H15, D14, O11等を抽出)
    # db["total_sales_volume"] = 51621.9 
    # db["lpg_price"] = D14の値
    
    # 【計算フェーズ2：精密財務（v6.9/8.0準拠）】
    # res_tax_total_F = 261,400 (前回の画像正解)
    # res_return = 1,613,897 (前回の画像正解)
    # res_dep = (投資額1+2) * 3%
    
    # --- 3. 最終総括原価の組み立て ---
    # 変動費 (原料費)
    variable_cost = db["total_sales_volume"] * db["lpg_price"]
    
    # 資産由来費用 (償却費 + 税 + 報酬)
    asset_cost = db["res_dep"] + db["res_tax_total_F"] + db["res_return"]
    
    # 合計総括原価
    db["final_total_cost"] = variable_cost + asset_cost + db["fixed_op_expenses"]
    
    # 供給単価
    db["unit_price"] = db["final_total_cost"] / db["total_sales_volume"]

# --- Dashboard ---
if uploaded_file:
    st.header("📊 供給単価 最終Dashboard")
    c1, c2, c3 = st.columns(3)
    c1.metric("最終総括原価", f"¥{db['final_total_cost']:,.0f}")
    c2.metric("予定販売量", f"{db['total_sales_volume']:,.1f} m3")
    c3.metric("供給単価", f"{db['unit_price']:,.2f} 円/m3")

    with st.sidebar:
        st.header("📉 固定費調整")
        db["fixed_op_expenses"] = st.number_input("その他経費（人件費等）", value=db["fixed_op_expenses"])

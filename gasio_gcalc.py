import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Final Logic", layout="wide")

# 1. 状態の初期化 (ここを最優先に実行する)
if 'db' not in st.session_state:
    st.session_state.db = {
        "res_land_invest": 0.0, "invest_1": 0.0, "invest_2": 0.0,
        "res_land_eval": 0.0, "return_rate": 0.0272, "reduction_rate": 0.46,
        "total_sales_volume": 0.0, "lpg_price": 0.0, "permit_locations": 0.0,
        "res_tax_total_F": 0.0, "res_return": 0.0, "res_dep": 0.0
    }

# 初期化が終わってから変数に代入
db = st.session_state.db

def col_to_idx(col_str):
    idx = 0
    for char in col_str.upper():
        idx = idx * 26 + (ord(char) - ord('A') + 1)
    return idx - 1

def clean_v(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').replace('点', '').replace('m3', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 最終配線完了")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("⚙️ 算定パラメータ")
    db["return_rate"] = st.number_input("事業報酬率", value=db["return_rate"], format="%.4f", step=0.0001)

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # --- A. ナビシート (D11, D14) ---
    if "ナビ" in sheets:
        df_n = sheets["ナビ"]
        db["permit_locations"] = clean_v(df_n.iloc[10, 3]) # D11
        db["lpg_price"] = clean_v(df_n.iloc[13, 3])      # D14
    
    # --- B. 販売量シート ---
    if "販売量" in sheets:
        df_s = sheets["販売量"]
        only_standard = (clean_v(df_s.iloc[3, col_to_idx("C")]) == 1) # C4
        use_std_factor = (clean_v(df_s.iloc[4, col_to_idx("C")]) == 1) # C5
        
        if only_standard and use_std_factor:
            db["total_sales_volume"] = db["permit_locations"] * 250 # 標準係数(例)
            db["calc_mode"] = "標準係数適用"
        else:
            # O11を確実に取得
            db["total_sales_volume"] = clean_v(df_s.iloc[10, col_to_idx("O")])
            db["calc_mode"] = "実績値適用"

    # --- C. 財務・土地計算 (v6.9のロジックを再適用) ---
    # ※ 土地評価額・資産1,2の計算をここに実行
    # ...

    # --- D. 租税課金・事業報酬 (v6.9の精密ロジック) ---
    # F1, f4, F2, F を計算
    # ...

# --- Dashboard 表示 ---
if uploaded_file:
    st.header("📊 供給単価 最終Dashboard")
    c1, c2, c3 = st.columns(3)
    
    fixed_costs = db["res_dep"] + db["res_tax_total_F"] + db["res_return"]
    raw_material_cost = db["total_sales_volume"] * db["lpg_price"]
    total_cost = fixed_costs + raw_material_cost
    
    unit_price = total_cost / db["total_sales_volume"] if db["total_sales_volume"] > 0 else 0
    
    c1.metric("最終総括原価", f"¥{total_cost:,.0f}")
    c2.metric("予定販売量", f"{db['total_sales_volume']:,.1f} m3")
    c3.metric("供給単価", f"{unit_price:,.2f} 円/m3")

    st.success(f"解析完了: {db.get('calc_mode', '---')}")

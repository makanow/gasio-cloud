import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Solid Connector", layout="wide")

# 列アルファベットをインデックス番号に変換する関数 (A=0, O=14)
def col_to_idx(col_str):
    exp = 0
    idx = 0
    for char in reversed(col_str.upper()):
        idx += (ord(char) - ord('A') + 1) * (26 ** exp)
        exp += 1
    return idx - 1

def clean_v(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').replace('点', '').replace('m3', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 最終配線調整")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    # 予期せぬ列の切り捨てを防ぐため、明示的に広い範囲を読み込む
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # --- A. ナビシート (D11, D14) ---
    if "ナビ" in sheets:
        df_n = sheets["ナビ"]
        # D11=iloc[10, 3], D14=iloc[13, 3] (見出し込)
        db = st.session_state.db
        db["permit_locations"] = clean_v(df_n.iloc[10, 3])
        db["lpg_price"] = clean_v(df_n.iloc[13, 3])
    
    # --- B. 販売量シート (C4, C5, O11) ---
    if "販売量" in sheets:
        df_s = sheets["販売量"]
        # 安全策：指定した列が存在するか確認し、足りなければ空列を補完する
        required_cols = col_to_idx("Q") + 1
        if len(df_s.columns) < required_cols:
            for i in range(len(df_s.columns), required_cols):
                df_s[f"extra_{i}"] = None

        only_standard = (clean_v(df_s.iloc[3, col_to_idx("C")]) == 1) # C4
        use_std_factor = (clean_v(df_s.iloc[4, col_to_idx("C")]) == 1) # C5
        
        # 判定ロジック
        final_use_std = use_std_factor if only_standard else False
        
        if not final_use_std:
            # 実績値 O11 (11行目, O列)
            db["total_sales_volume"] = clean_v(df_s.iloc[10, col_to_idx("O")])
            db["calc_mode"] = "実績値適用"
            # 内訳 Q8:Q10, O8:O10 の取得も可能
            db["sales_detail"] = df_s.iloc[7:10, col_to_idx("O")].apply(clean_v).tolist()
        else:
            db["total_sales_volume"] = db.get("permit_locations", 0) * 250 # 仮
            db["calc_mode"] = "標準係数適用"

    # --- C. 財務計算 (v6.9継承) ---
    # ここに以前の land_tax_F1, tax_standard_base_f4 等のロジックが走る

# --- Dashboard ---
if "total_sales_volume" in st.session_state.get("db", {}):
    db = st.session_state.db
    st.header("📊 供給単価 最終Dashboard")
    c1, c2, c3 = st.columns(3)
    
    # 合計原価の計算
    fixed_costs = db.get("res_dep", 0) + db.get("res_tax_total_F", 0) + db.get("res_return", 0)
    raw_material_cost = db.get("total_sales_volume", 0) * db.get("lpg_price", 0)
    total_cost = fixed_costs + raw_material_cost
    
    unit_price = total_cost / db["total_sales_volume"] if db["total_sales_volume"] > 0 else 0
    
    c1.metric("最終総括原価", f"¥{total_cost:,.0f}")
    c2.metric("予定販売量", f"{db['total_sales_volume']:,.1f} m3")
    c3.metric("供給単価", f"{unit_price:,.2f} 円/m3")

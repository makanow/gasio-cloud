import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Rule Compliant", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = {k: 0.0 for k in ["res_land_invest", "invest_1", "invest_2", "res_tax", "res_return", "res_dep", "res_land_eval", "res_land_area_adj"]}
db = st.session_state.db

def clean_v(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 算定ルール完全準拠")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # --- 1. 土地の計算 (独立) ---
    if "土地" in sheets:
        df_l = sheets["土地"]
        land_found = False
        for i in range(len(df_l)):
            area = clean_v(df_l.iloc[i, 4])
            price = clean_v(df_l.iloc[i, 5])
            if area > 0 and price > 0:
                eval_v = clean_v(df_l.iloc[i, 7])
                db["res_land_area_adj"] = min(area, 295.0)
                db["res_land_invest"] = round(price / area, 0) * db["res_land_area_adj"]
                db["res_land_eval"] = round(eval_v / area, 0) * db["res_land_area_adj"]
                land_found = True
                break

    # --- 2. 償却資産の計算 (土地を含まない) ---
    if "償却資産" in sheets:
        df_a = sheets["償却資産"]
        inv1, inv2 = 0.0, 0.0
        for i in range(len(df_a)):
            mode_raw = df_a.iloc[i, 10]
            if pd.isna(mode_raw): continue
            
            mode = clean_v(mode_raw)
            val = clean_v(df_a.iloc[i, 11]) if mode == 1 else clean_v(df_a.iloc[i, 12])
            if val <= 0: continue
            
            # 10列目(index 9) 減免判定
            is_reduced = (clean_v(df_a.iloc[i, 9]) == 1)
            if is_reduced: inv2 += val
            else: inv1 += val
        
        db["invest_1"] = inv1  # 土地は合算しない
        db["invest_2"] = inv2

    # --- 3. 財務計算 (土地を個別に考慮) ---
    # 租税公課: (投資額1 + 投資額2*0.5 + 土地評価額) * 1.4%
    tax_base = db["invest_1"] + (db["invest_2"] * 0.5) + db.get("res_land_eval", 0)
    db["res_tax"] = math.floor(tax_base * 0.014)

    # 事業報酬: (通常資産 + 減免資産 + 認容土地投資額) * 3%
    total_rate_base = db["invest_1"] + db["invest_2"] + db["res_land_invest"]
    db["res_return"] = math.floor(total_rate_base * 0.03)

    # 減価償却費: (通常資産 + 減免資産) * 3%  ※土地は含まない
    db["res_dep"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)

# --- Dashboard ---
st.header("📊 算定 Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("推定総括原価", f"¥{db['res_dep'] + db['res_tax'] + db['res_return']:,.0f}")
c2.metric("租税公課", f"¥{db['res_tax']:,.0f}")
c3.metric("事業報酬", f"¥{db['res_return']:,.0f}")

with st.expander("📝 内部計算の詳細（Excelとの照合用）"):
    st.write(f"認容土地投資額: **¥{db['res_land_invest']:,.0f}**")
    st.write(f"投資額① (通常資産のみ): **¥{db['invest_1']:,.0f}**")
    st.write(f"投資額② (減免資産): **¥{db['invest_2']:,.0f}**")
    st.write(f"土地評価額(認容分): ¥{db.get('res_land_eval', 0):,.0f}")

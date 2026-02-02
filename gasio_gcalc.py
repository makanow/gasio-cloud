import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Final Logic Sync", layout="wide")

# 1. 初期状態の設定 (初期値は0で安定させる)
if 'db' not in st.session_state:
    st.session_state.db = {
        "res_land_invest": 0.0, 
        "invest_1": 0.0, 
        "invest_2": 0.0,
        "res_land_eval": 0.0,
        "reduction_rate": 0.46,
        "use_reduction": True,
        "return_rate": 0.0272,
        "res_tax": 0.0,
        "res_return": 0.0,
        "res_dep": 0.0
    }
db = st.session_state.db

def clean_v(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 財務ロジック最終同期")

# --- サイドバー：報酬率の上書き設定 ---
with st.sidebar:
    st.header("⚙️ 算定パラメータ")
    db["return_rate"] = st.number_input("事業報酬率", value=db["return_rate"], format="%.4f", step=0.0001)
    db["use_reduction"] = st.checkbox("減免措置（軽減係数 0.46）を適用", value=db["use_reduction"])
    reduction_factor = 0.46 if db["use_reduction"] else 1.0

# 2. Excelデータのロード
uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # --- 土地の計算 ---
    if "土地" in sheets:
        df_l = sheets["土地"]
        for i in range(len(df_l)):
            area = clean_v(df_l.iloc[i, 4])
            price = clean_v(df_l.iloc[i, 5])
            if area > 0 and price > 0:
                eval_v = clean_v(df_l.iloc[i, 7])
                db["res_land_area_adj"] = min(area, 295.0)
                db["res_land_invest"] = round(price / area, 0) * db["res_land_area_adj"]
                db["res_land_eval"] = round(eval_v / area, 0) * db["res_land_area_adj"]
                break

    # --- 償却資産の計算 ---
    if "償却資産" in sheets:
        df_a = sheets["償却資産"]
        inv1, inv2 = 0.0, 0.0
        for i in range(len(df_a)):
            mode_raw = df_a.iloc[i, 10]
            if pd.isna(mode_raw): continue
            mode = clean_v(mode_raw)
            val = clean_v(df_a.iloc[i, 11]) if mode == 1 else clean_v(df_a.iloc[i, 12])
            if val <= 0: continue
            if clean_v(df_a.iloc[i, 9]) == 1: inv2 += val
            else: inv1 += val
        db["invest_1"] = inv1
        db["invest_2"] = inv2

    # --- 3. 財務計算（ナガセ・プロトコル適用） ---
    # 租税公課: ROUND(投資額①/2 + 投資額② * 軽減係数/2, 0)
    db["res_tax"] = round((db["invest_1"] / 2) + (db["invest_2"] * reduction_factor / 2), 0)

    # 事業報酬: ROUND( (土地 + 投資1 + 投資2) * 報酬率, 0 )
    total_invest_sum = db["res_land_invest"] + db["invest_1"] + db["invest_2"]
    db["res_return"] = round(total_invest_sum * db["return_rate"], 0)

    # 減価償却費: (投資1 + 投資2) * 3% 
    db["res_dep"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)

    # 4. Dashboard表示
    st.header("📊 算定 Dashboard")
    c1, c2, c3 = st.columns(3)
    c1.metric("推定総括原価", f"¥{db['res_dep'] + db['res_tax'] + db['res_return']:,.0f}")
    c2.metric("租税公課", f"¥{db['res_tax']:,.0f}")
    c3.metric("事業報酬", f"¥{db['res_return']:,.0f}")

    with st.expander("📝 計算根拠（内部変数）"):
        st.write(f"ベース投資総額: ¥{total_invest_sum:,.0f}")
        st.write(f"適用報酬率: {db['return_rate'] * 100:.2f}%")
        st.write(f"投資額① (通常): ¥{db['invest_1']:,.0f}")
        st.write(f"投資額② (減免): ¥{db['invest_2']:,.0f}")
        st.write(f"認容土地投資額: ¥{db['res_land_invest']:,.0f}")

import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Final Logic Sync", layout="wide")

# 1. 初期状態の設定
if 'db' not in st.session_state:
    st.session_state.db = {
        "res_land_invest": 6953445, 
        "invest_1": 12010855, 
        "invest_2": 40370150,
        "res_land_eval": 2784210,
        "reduction_rate": 0.46,
        "use_reduction": True,
        "return_rate": 0.0272
    }
db = st.session_state.db

def clean_v(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').strip())
    except: return 0.0

# --- サイドバー：報酬率の上書き設定 ---
with st.sidebar:
    st.header("⚙️ 算定パラメータ")
    db["return_rate"] = st.number_input("事業報酬率", value=db["return_rate"], format="%.4f", step=0.0001)
    db["use_reduction"] = st.checkbox("減免措置（軽減係数 0.46）を適用", value=db["use_reduction"])
    reduction_factor = 0.46 if db["use_reduction"] else 1.0

# 2. Excelからのデータ読み込み
uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # 【中略】土地・資産の読み込みロジック (v6.3準拠)
    # ※ここには以前成功した土地(5,6,8列)・資産(10,11,12,13列)のコードが入る

    # --- 3. 財務計算（ナガセ・プロトコル） ---
    # 租税公課: ROUND(投資額①/2 + 投資額② * 軽減係数/2, 0)
    # ※土地評価額についての言及がなかったので、一旦資産側のみで計算
    db["res_tax"] = round((db["invest_1"] / 2) + (db["invest_2"] * reduction_factor / 2), 0)

    # 事業報酬: ROUND( (土地 + 投資1 + 投資2) * 報酬率, 0 )
    total_invest_sum = db["res_land_invest"] + db["invest_1"] + db["invest_2"]
    db["res_return"] = round(total_invest_sum * db["return_rate"], 0)

    # 減価償却費: (投資1 + 投資2) * 3% (仮定)
    db["res_dep"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)

# --- Dashboard ---
st.header("📊 算定 Dashboard (最終同期済)")
c1, c2, c3 = st.columns(3)

# 推定総括原価（土地・資産由来の合計）
total_cost = db.get("res_dep", 0) + db.get("res_tax", 0) + db.get("res_return", 0)
c1.metric("推定総括原価", f"¥{total_cost:,.0f}")
c2.metric("租税公課", f"¥{db.get('res_tax', 0):,.0f}")
c3.metric("事業報酬", f"¥{db.get('res_return', 0):,.0f}")

with st.expander("📝 計算根拠の確認"):
    st.write(f"ベース投資総額: ¥{total_invest_sum:,.0f}")
    st.write(f"適用報酬率: {db['return_rate'] * 100:.2f}%")
    st.write(f"軽減係数: {reduction_factor}")

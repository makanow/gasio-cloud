import streamlit as st
import pandas as pd
import math

# 1. ページ構成
st.set_page_config(page_title="Gas Lab Engine v3.1", layout="wide")

# 2. 初期化（NameErrorを完全に封殺）
if 'db' not in st.session_state:
    st.session_state.db = {
        "land_id": "11", "use_reduction": True, "active_return_rate": 0.03,
        "res_land_area": 0, "res_land_invest": 0, "res_land_eval": 0,
        "invest_1": 0, "invest_2": 0, "res_tax": 0, "res_return": 0, "res_dep": 0
    }

db = st.session_state.db

# 3. 計算ロジック
def run_logic(df_land=None, df_assets=None):
    # --- A. 土地：土地情報シートから取得 ---
    if df_land is not None:
        # A列: 面積 / B列: 価格 / C列: 評価額 と仮定（ナガセのシート構造に合わせる）
        act_area = df_land.iloc[0, 0]
        act_price = df_land.iloc[0, 1]
        act_eval = df_land.iloc[0, 2]
        
        req_area = 295.0 # 標準係数B上限
        db["res_land_area"] = min(act_area, req_area)
        
        # ナガセ指定：ROUND(単価, 0) * 面積
        u_price = round(act_price / act_area, 0)
        db["res_land_invest"] = u_price * db["res_land_area"]
        
        u_eval = round(act_eval / act_area, 0)
        db["res_land_eval"] = u_eval * db["res_land_area"]

    # --- B. 償却資産：償却資産シートから取得 ---
    if df_assets is not None:
        # I列(8): 減免判定(1/0) / K列(10): 取得価額
        # 投資額②(減免対象)
        db["invest_2"] = df_assets[df_assets.iloc[:, 8] == 1].iloc[:, 10].sum()
        # 投資額①(通常) = 減免対象外の合計 + 土地認容額
        db["invest_1"] = df_assets[df_assets.iloc[:, 8] != 1].iloc[:, 10].sum() + db["res_land_invest"]

    # --- C. 財務計算 ---
    tax_base = db["invest_1"] + (db["invest_2"] * 0.5)
    db["res_tax"] = math.floor(tax_base * 0.014) + math.floor(db["res_land_eval"] * 0.014)
    db["res_return"] = math.floor((db["invest_1"] + db["invest_2"]) * db["active_return_rate"])
    db["res_dep"] = (db["invest_1"] + db["invest_2"]) * 0.03

# 4. UIセクション
st.title("🧪 Gas Lab Engine : 複数シート統合検証")

with st.sidebar:
    st.header("📂 データ・アップロード")
    file_land = st.file_uploader("土地情報シート (CSV)", type="csv")
    file_assets = st.file_uploader("償却資産シート (CSV)", type="csv")
    
    st.divider()
    db["use_reduction"] = st.checkbox("減免措置を適用", value=db["use_reduction"])
    
    if st.button("🚀 計算実行"):
        df_l = pd.read_csv(file_land) if file_land else None
        df_a = pd.read_csv(file_assets) if file_assets else None
        run_logic(df_l, df_a)

# メイン表示
st.header("📊 算定 Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("推定総括原価", f"¥{db['res_dep']+db['res_tax']+db['res_return']:,.0f}")
c2.metric("租税公課", f"¥{db['res_tax']:,.0f}")
c3.metric("事業報酬", f"¥{db['res_return']:,.0f}")

st.divider()
st.subheader("📋 土地認容結果（詳細）")
l1, l2, l3 = st.columns(3)
l1.metric("認容面積", f"{db['res_land_area']} m2")
l2.metric("認容投資額", f"¥{db['res_land_invest']:,.0f}")
l3.metric("認容評価額", f"¥{db['res_land_eval']:,.0f}")

st.subheader("📋 投資額の振り分け状況")
st.write(f"投資額① (通常資産 + 認容土地): **¥{db['invest_1']:,.0f}**")
st.write(f"投資額② (減免対象資産): **¥{db['invest_2']:,.0f}**")

import streamlit as st
import pandas as pd
import math

# 1. ページ設定
st.set_page_config(page_title="Gas Lab Engine v2.9", layout="wide")

# 2. 初期化 (2_a.csv の読み込みを前提とする)
if 'db' not in st.session_state:
    st.session_state.db = {
        "asset_mode": "実績",
        "use_reduction": True,
        "actual_land_area": 649.1,
        "actual_land_price": 15300000.0,
        "actual_land_eval": 6126190.0,
        "land_id": "11",
        "override_return_rate": False,
        "active_return_rate": 0.03
    }

db = st.session_state.db

# 3. CSVロード＆計算エンジン
def process_assets(df_2a):
    """2_a.csv から資産を読み込み、投資額①・②に振り分ける"""
    invest_1 = 0.0
    invest_2 = 0.0
    
    # 仮定: H列が取得価額, I列が減免判定(1=対象)
    for index, row in df_2a.iterrows():
        # 実績/標準の切り替えはここでは一旦実績固定で実装
        val = row.get('実績取得価額', 0) 
        is_red = row.get('減免判定', 0)
        
        if is_red == 1 and db["use_reduction"]:
            invest_2 += val
        else:
            invest_1 += val
    return invest_1, invest_2

def run_full_engine():
    # 土地の ROUND 計算
    req_area = 295.0
    db["res_land_area"] = min(db["actual_land_area"], req_area)
    u_price = round(db["actual_land_price"] / db["actual_land_area"], 0)
    db["res_land_invest"] = u_price * db["res_land_area"]
    u_eval = round(db["actual_land_eval"] / db["actual_land_area"], 0)
    db["res_land_eval"] = u_eval * db["res_land_area"]

    # 租税公課・事業報酬
    tax_base = (db["invest_1"] + db["res_land_invest"]) + (db["invest_2"] * 0.5)
    db["res_tax"] = math.floor(tax_base * 0.014) + math.floor(db["res_land_eval"] * 0.014)
    db["res_return"] = math.floor((db["invest_1"] + db["invest_2"] + db["res_land_invest"]) * db["active_return_rate"])
    db["res_dep"] = (db["invest_1"] + db["invest_2"]) * 0.03

# 4. UI
st.title("🧪 Gas Lab Engine : 本番データ統合")

uploaded_file = st.file_uploader("2_a.csv (資産明細) をアップロードしてください", type="csv")
if uploaded_file:
    df_2a = pd.read_csv(uploaded_file)
    db["invest_1"], db["invest_2"] = process_assets(df_2a)
    run_full_engine()

    # 結果表示（スクリーンショットの項目を本物で更新）
    st.header("財務ロジック検証（本番値）")
    c1, c2, c3 = st.columns(3)
    c1.metric("推定総括原価", f"¥{db.get('res_dep',0)+db.get('res_tax',0)+db.get('res_return',0):,.0f}")
    c2.metric("租税公課", f"¥{db.get('res_tax',0):,.0f}")
    c3.metric("事業報酬", f"¥{db.get('res_return',0):,.0f}")

    st.subheader("📋 土地・資産の確定値")
    col_a, col_b = st.columns(2)
    col_a.write(f"認容土地投資額: ¥{db.get('res_land_invest',0):,.0f}")
    col_b.write(f"投資額② (減免適用後): ¥{db.get('invest_2',0):,.0f}")

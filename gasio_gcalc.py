import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Precision Sync", layout="wide")

# 1. 初期化
if 'db' not in st.session_state:
    st.session_state.db = {k: 0.0 for k in ["res_land_invest", "invest_1", "invest_2", "res_tax", "res_return", "res_dep"]}
db = st.session_state.db

def clean_v(val):
    try:
        if pd.isna(val): return 0.0
        return float(str(val).replace(',', '').replace('¥', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : Precision Mode")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    # データ読み込み（全てのシート）
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # --- A. 土地の精密抽出 ---
    # スクリーンショットの検知結果 [15行, 5列] = インデックスでは [13, 4]
    if "土地" in sheets:
        df_l = sheets["土地"]
        # 君のExcelの配置に合わせてここを微調整
        db["res_land_area"] = clean_v(df_l.iloc[13, 4])  # 15行目 5列目
        v_price = clean_v(df_l.iloc[13, 5])              # その隣を価格と仮定
        
        if db["res_land_area"] > 0:
            db["res_land_area_adj"] = min(db["res_land_area"], 295.0)
            db["res_land_invest"] = round(v_price / db["res_land_area"], 0) * db["res_land_area_adj"]

    # --- B. 資産の精密抽出 (償却資産シート) ---
    target_asset_sheet = next((s for s in sheets.keys() if "償却資産" in s or "2_a" in s), None)
    if target_asset_sheet:
        df_a = sheets[target_asset_sheet]
        # ナガセのExcel構造：I列(8)=減免判定, K列(10)=取得価額
        # 1行目が見出しと仮定して2行目からスキャン
        prices = df_a.iloc[1:, 10].apply(clean_v)
        flags = df_a.iloc[1:, 8].apply(clean_v)
        
        db["invest_2"] = prices[flags == 1].sum()
        db["invest_1"] = prices[flags != 1].sum() + db["res_land_invest"]

    # --- C. 財務・税金ロジック ---
    tax_base = db["invest_1"] + (db["invest_2"] * 0.5)
    db["res_tax"] = math.floor(tax_base * 0.014)
    # 事業報酬 (3%) と 減価償却 (3%)
    db["res_return"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)
    db["res_dep"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)

# --- Dashboard ---
st.header("📊 算定 Dashboard (精密検証)")
c1, c2, c3 = st.columns(3)
c1.metric("推定総括原価", f"¥{db['res_dep'] + db['res_tax'] + db['res_return']:,.0f}")
c2.metric("租税公課", f"¥{db['res_tax']:,.0f}")
c3.metric("事業報酬", f"¥{db['res_return']:,.0f}")

st.divider()
st.subheader("📋 内部計算チェック")
st.write(f"土地投資額（認容後）: ¥{db['res_land_invest']:,.0f}")
st.write(f"償却資産① (通常): ¥{db['invest_1'] - db['res_land_invest']:,.0f}")
st.write(f"償却資産② (減免): ¥{db['invest_2']:,.0f}")

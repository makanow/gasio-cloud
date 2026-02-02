import streamlit as st
import pandas as pd
import math

# 1. ページ設定
st.set_page_config(page_title="Gas Lab Engine : Final Ver", layout="wide")

# 2. 初期化
if 'db' not in st.session_state:
    st.session_state.db = {
        "res_land_invest": 0, "invest_1": 0, "invest_2": 0,
        "res_tax": 0, "res_return": 0, "res_dep": 0
    }
db = st.session_state.db

# 3. 数値クレンジング（Excelの書式対策）
def clean_v(val):
    try:
        if pd.isna(val): return 0.0
        return float(str(val).replace(',', '').strip())
    except: return 0.0

# 4. メイン計算エンジン
def run_master_logic(sheets):
    # --- 土地認容判定 ---
    # シート名に「土地」が含まれるものを探す
    land_sn = [s for s in sheets.keys() if "土地" in s]
    if land_sn:
        df_l = sheets[land_sn[0]]
        act_area = clean_v(df_l.iloc[0, 0])
        act_price = clean_v(df_l.iloc[0, 1])
        act_eval = clean_v(df_l.iloc[0, 2])
        if act_area > 0:
            db["res_land_area"] = min(act_area, 295.0)
            db["res_land_invest"] = round(act_price / act_area, 0) * db["res_land_area"]
            db["res_land_eval"] = round(act_eval / act_area, 0) * db["res_land_area"]

    # --- 償却資産集計 ---
    # シート名に「資産」が含まれるものを探す
    asset_sn = [s for s in sheets.keys() if "資産" in s]
    if asset_sn:
        df_a = sheets[asset_sn[0]]
        # I列(8): 減免フラグ / K列(10): 取得価額
        vals = df_a.iloc[:, 10].apply(clean_v)
        is_red = df_a.iloc[:, 8]
        db["invest_2"] = vals[is_red == 1].sum()
        db["invest_1"] = vals[is_red != 1].sum() + db.get("res_land_invest", 0)

    # --- 財務諸元 ---
    tax_base = db["invest_1"] + (db["invest_2"] * 0.5)
    db["res_tax"] = math.floor(tax_base * 0.014) + math.floor(db.get("res_land_eval", 0) * 0.014)
    db["res_return"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03) # 3%
    db["res_dep"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03) # 3%

# --- UI ---
st.title("🧪 Gas Lab Engine : Excel Direct Loader")
st.info("GitHub連携が404になるため、手元の 'G-Calc_master.xlsx' をアップロードしてください。")

uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"])

if uploaded_file:
    # 全シートを読み込み（数式ではなく「値」を抽出）
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
    run_master_logic(all_sheets)
    st.success("Excelの解析が完了しました。")

# Dashboard
st.header("📊 算定 Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("推定総括原価", f"¥{db['res_dep']+db['res_tax']+db['res_return']:,.0f}")
c2.metric("租税公課", f"¥{db['res_tax']:,.0f}")
c3.metric("事業報酬", f"¥{db['res_return']:,.0f}")

st.divider()
st.subheader("📋 内訳確認")
st.write(f"土地認容投資額: ¥{db.get('res_land_invest', 0):,.0f}")
st.write(f"投資額① (通常資産): ¥{db.get('invest_1', 0):,.0f}")
st.write(f"投資額② (減免資産): ¥{db.get('invest_2', 0):,.0f}")

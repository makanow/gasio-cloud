import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Final Logic", layout="wide")

# 初期化
if 'db' not in st.session_state:
    st.session_state.db = {k: 0.0 for k in ["res_land_invest", "invest_1", "invest_2", "res_tax", "res_return", "res_dep"]}
db = st.session_state.db

def clean_v(val):
    try:
        if pd.isna(val): return 0.0
        return float(str(val).replace(',', '').replace('¥', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 最終ロジック統合")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # --- 1. 土地の計算（5列目=面積, 6列目=価格, 8列目=評価額） ---
    # Pythonのインデックスは0から始まるため、5列目=iloc[:,4], 6列目=iloc[:,5], 8列目=iloc[:,7]
    if "土地" in sheets:
        df_l = sheets["土地"]
        # データが2行目からと仮定（ヘッダーがある場合）
        area = clean_v(df_l.iloc[0, 4])
        price = clean_v(df_l.iloc[0, 5])
        eval_v = clean_v(df_l.iloc[0, 7])
        
        if area > 0:
            db["res_land_area_adj"] = min(area, 295.0)
            db["res_land_invest"] = round(price / area, 0) * db["res_land_area_adj"]
            db["res_land_eval"] = round(eval_v / area, 0) * db["res_land_area_adj"]

    # --- 2. 償却資産の計算 ---
    # 10列目(index 9)=減免フラグ, 11列目(index 10)=0(標準)/1(実績)
    # 12列目(index 11)=実績額, 13列目(index 12)=標準額
    if "償却資産" in sheets:
        df_a = sheets["償却資産"]
        inv1, inv2 = 0.0, 0.0
        
        for i in range(len(df_a)):
            # 参照先判定（11列目）
            mode = clean_v(df_a.iloc[i, 10])
            val = clean_v(df_a.iloc[i, 11]) if mode == 1 else clean_v(df_a.iloc[i, 12])
            
            # 減免判定（10列目）
            is_reduced = (clean_v(df_a.iloc[i, 9]) == 1)
            
            if is_reduced:
                inv2 += val
            else:
                inv1 += val
        
        db["invest_1"] = inv1 + db.get("res_land_invest", 0)
        db["invest_2"] = inv2

    # --- 3. 財務諸元 ---
    # 租税公課: (投資1 + 投資2*0.5 + 土地評価額) * 1.4%
    tax_base = db["invest_1"] + (db["invest_2"] * 0.5)
    db["res_tax"] = math.floor(tax_base * 0.014) + math.floor(db.get("res_land_eval", 0) * 0.014)
    # 事業報酬 & 減価償却 (3%仮定)
    total_asset = db["invest_1"] + db["invest_2"]
    db["res_return"] = math.floor(total_asset * 0.03)
    db["res_dep"] = math.floor((total_asset - db.get("res_land_invest", 0)) * 0.03)

# --- Dashboard ---
st.header("📊 算定 Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("推定総括原価", f"¥{db['res_dep'] + db['res_tax'] + db['res_return']:,.0f}")
c2.metric("租税公課", f"¥{db['res_tax']:,.0f}")
c3.metric("事業報酬", f"¥{db['res_return']:,.0f}")

with st.expander("📝 内部計算の詳細"):
    st.write(f"認容土地投資額: ¥{db.get('res_land_invest', 0):,.0f}")
    st.write(f"投資額① (通常): ¥{db['invest_1']:,.0f}")
    st.write(f"投資額② (減免): ¥{db['invest_2']:,.0f}")

import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Final Recovery", layout="wide")

# 初期化（聖数 30,715,365 への器）
if 'db' not in st.session_state:
    st.session_state.db = {k: 0.0 for k in ["res_land_invest", "res_land_area", "res_land_eval", "invest_1", "invest_2"]}
db = st.session_state.db

def try_float(val):
    try:
        if pd.isna(val): return None
        return float(str(val).replace(',', '').replace('㎡', '').replace('円', '').strip())
    except: return None

st.title("🧪 Gas Lab Engine : Auto Discovery Mode")

# クラウドが無理と言われないための「確実な搬入口」
uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード（ドラッグ＆ドロップ）", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # 【全自動スキャン】「土地」と「資産」の場所を総当たりで探す
    for s_name, df in sheets.items():
        # A. 土地データの探索
        if "土地" in s_name:
            for r in range(len(df)):
                for c in range(len(df.columns) - 1):
                    v_area = try_float(df.iloc[r, c])
                    v_price = try_float(df.iloc[r, c+1])
                    if v_area and v_area > 0 and v_price and v_price > 0:
                        db["res_land_area"] = min(v_area, 295.0)
                        db["res_land_invest"] = round(v_price / v_area, 0) * db["res_land_area"]
                        st.sidebar.success(f"土地発見: {s_name} [{r+2}行, {c+1}列]")
                        break
        
        # B. 償却資産データの探索（I列=減免, K列=取得価額）
        if "資産" in s_name or "2_a" in s_name:
            # 11列目(K列)に数値があり、9列目(I列)にフラグがある場所を探す
            try:
                # 文字列を排除して数値化
                prices = df.iloc[:, 10].apply(try_float).fillna(0)
                is_red = df.iloc[:, 8].apply(try_float).fillna(0)
                db["invest_2"] = prices[is_red == 1].sum()
                db["invest_1"] = prices[is_red != 1].sum() + db["res_land_invest"]
                st.sidebar.success(f"資産発見: {s_name}")
            except: continue

# --- Dashboard ---
st.header("📊 算定 Dashboard (自動検知)")
c1, c2, c3 = st.columns(3)
c1.metric("認容土地投資額", f"¥{db['res_land_invest']:,.0f}")
c2.metric("投資額① (通常)", f"¥{db['invest_1']:,.0f}")
c3.metric("投資額② (減免)", f"¥{db['invest_2']:,.0f}")

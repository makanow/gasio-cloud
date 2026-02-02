import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Adjuster", layout="wide")

# 初期化
if 'db' not in st.session_state:
    st.session_state.db = {k: 0 for k in ["res_land_invest", "res_land_area", "res_land_eval", "invest_1", "invest_2"]}
db = st.session_state.db

def clean_num(val):
    try:
        if pd.isna(val): return 0.0
        return float(str(val).replace(',', '').replace('㎡', '').replace('円', '').strip())
    except: return None # 数値化できない場合はNoneを返す

st.title("🧪 Gas Lab Engine : Land Data Fix")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # 1. 「土地」シートの解析
    land_sheet = next((s for s in sheets.keys() if "土地" in s), None)
    if land_sheet:
        df_l = sheets[land_sheet]
        
        # 【重要】数値が入っている最初の行を探す（見出しスキップ）
        valid_row = None
        for i in range(len(df_l)):
            # 1列目(面積)と2列目(価格)が両方数値になれる行を探す
            area_test = clean_num(df_l.iloc[i, 0])
            price_test = clean_num(df_l.iloc[i, 1])
            if area_test is not None and price_test is not None:
                valid_row = i
                break
        
        if valid_row is not None:
            # 確定データの取得
            act_area = clean_num(df_l.iloc[valid_row, 0])
            act_price = clean_num(df_l.iloc[valid_row, 1])
            act_eval = clean_num(df_l.iloc[valid_row, 2])
            
            # ナガセ指定ロジック：ROUND(価格/面積, 0) * MIN(面積, 295)
            db["res_land_area"] = min(act_area, 295.0)
            unit_p = round(act_price / act_area, 0)
            db["res_land_invest"] = unit_p * db["res_land_area"]
            
            unit_e = round(act_eval / act_area, 0)
            db["res_land_eval"] = unit_e * db["res_land_area"]
            
            st.success(f"✅ シート '{land_sheet}' の {valid_row + 1} 行目をデータとして認識しました。")
        else:
            st.error(f"❌ シート '{land_sheet}' 内に有効な数値データが見つかりません。")

# Dashboard
st.header("📊 土地算定プレビュー")
col1, col2, col3 = st.columns(3)
col1.metric("認容面積", f"{db['res_land_area']} m2")
col2.metric("認容投資額", f"¥{db['res_land_invest']:,.0f}")
col3.metric("認容評価額", f"¥{db['res_land_eval']:,.0f}")

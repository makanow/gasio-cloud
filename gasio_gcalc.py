import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Final Stability", layout="wide")

# 初期化
if 'db' not in st.session_state:
    st.session_state.db = {k: 0.0 for k in ["res_land_invest", "res_land_area", "res_land_eval"]}
db = st.session_state.db

def clean_num(val):
    try:
        if pd.isna(val): return None
        # 文字列としてカンマ等を除去
        s = str(val).replace(',', '').replace('㎡', '').replace('円', '').strip()
        num = float(s)
        return num
    except: return None

st.title("🧪 Gas Lab Engine : Land Calc Verified")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    try:
        sheets = pd.read_excel(uploaded_file, sheet_name=None)
        land_sheet = next((s for s in sheets.keys() if "土地" in s), None)
        
        if land_sheet:
            df_l = sheets[land_sheet]
            valid_row = None
            
            # 数値が入っている「かつ」面積が0より大きい行を探す
            for i in range(len(df_l)):
                area_val = clean_num(df_l.iloc[i, 0])
                price_val = clean_num(df_l.iloc[i, 1])
                # 面積がNoneでなく、かつ0より大きいことを厳格にチェック
                if area_val is not None and area_val > 0:
                    if price_val is not None:
                        valid_row = i
                        break
            
            if valid_row is not None:
                act_area = clean_num(df_l.iloc[valid_row, 0])
                act_price = clean_num(df_l.iloc[valid_row, 1])
                act_eval = clean_num(df_l.iloc[valid_row, 2]) or 0.0
                
                # 計算実行（act_area > 0 が保証されているので安全）
                db["res_land_area"] = min(act_area, 295.0)
                unit_p = round(act_price / act_area, 0)
                db["res_land_invest"] = unit_p * db["res_land_area"]
                
                unit_e = round(act_eval / act_area, 0)
                db["res_land_eval"] = unit_e * db["res_land_area"]
                
                st.success(f"✅ シート '{land_sheet}' の {valid_row + 1} 行目を正常に解析しました。")
            else:
                st.error("❌ 面積が 0 より大きい有効なデータ行が見つかりません。")
    except Exception as e:
        st.error(f"予期せぬエラー: {e}")

# Dashboard
st.header("📊 土地算定 Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("認容面積", f"{db['res_land_area']} m2")
c2.metric("認容投資額", f"¥{db['res_land_invest']:,.0f}")
c3.metric("認容評価額", f"¥{db['res_land_eval']:,.0f}")

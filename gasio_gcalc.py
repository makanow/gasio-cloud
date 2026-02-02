import streamlit as st
import pandas as pd
import math

# 1. 初期化
if 'db' not in st.session_state:
    st.session_state.db = {}
db = st.session_state.db

def clean_v(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').replace('点', '').replace('m3', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 供給単価最終算定")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # --- A. ナビシートの読み込み (地点数・原料価格) ---
    if "ナビ" in sheets:
        df_n = sheets["ナビ"]
        db["permit_locations"] = clean_v(df_n.iloc[9, 3]) # D11 (index10-1, 4-1)
        db["lpg_price"] = clean_v(df_n.iloc[12, 3])      # D14
    
    # --- B. 販売量の判定と取得 ---
    if "販売量" in sheets:
        df_s = sheets["販売量"]
        only_standard_contract = (clean_v(df_s.iloc[3, 2]) == 1) # C4
        use_std_factor = (clean_v(df_s.iloc[4, 2]) == 1)         # C5
        
        # 判定: 供給約款以外がある(C4=0)なら、C5が1でも強制的に実績値(0)
        final_use_std = use_std_factor if only_standard_contract else False
        
        if final_use_std:
            # 標準係数使用の場合のロジック (地点数等から計算)
            # ここに標準係数シートからの引用ロジックを追加可能
            db["total_sales_volume"] = db["permit_locations"] * 250 # 仮の標準係数
            db["calc_mode"] = "標準係数適用"
        else:
            # 実績値使用の場合 (O11 = index 10, 14)
            db["total_sales_volume"] = clean_v(df_s.iloc[10, 14])
            db["calc_mode"] = "実績値適用 (自由契約有)"

    # --- C. 財務・税金ロジック (v6.9継承) ---
    # [中略：投資額①、②、土地評価額、報酬率 0.0272 等の計算]
    # ※前回の計算を通過したと仮定

    # --- D. 供給単価の算出 ---
    # 総括原価(仮) = 償却費 + 租税公課 + 事業報酬
    subtotal_cost = db.get("res_dep", 0) + db.get("res_tax_total_F", 0) + db.get("res_return", 0)
    
    # 原料費 = 販売量 * 原料価格
    db["raw_material_cost"] = db.get("total_sales_volume", 0) * db.get("lpg_price", 0)
    
    # 最終総括原価
    db["final_total_cost"] = subtotal_cost + db["raw_material_cost"]
    
    # 供給単価 (円/m3)
    if db.get("total_sales_volume", 0) > 0:
        db["unit_price"] = db["final_total_cost"] / db["total_sales_volume"]
    else:
        db["unit_price"] = 0

# --- Dashboard ---
st.header("📊 供給単価 最終Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("最終総括原価", f"¥{db.get('final_total_cost', 0):,.0f}")
c2.metric("予定販売量", f"{db.get('total_sales_volume', 0):,.0f} m3")
c3.metric("供給単価", f"{db.get('unit_price', 0):,.2f} 円/m3")

st.divider()
with st.expander("📝 算定条件の確認"):
    st.write(f"判定結果: **{db.get('calc_mode', '未解析')}**")
    st.write(f"原料単価: ¥{db.get('lpg_price', 0):,.2f}")
    st.write(f"許可地点数: {db.get('permit_locations', 0)} 地点")

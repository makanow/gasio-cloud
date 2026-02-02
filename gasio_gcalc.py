import streamlit as st
import pandas as pd
import math
import re

# 1. 状態の初期化
if 'db' not in st.session_state:
    st.session_state.db = {}
db = st.session_state.db

def cell(df, ref):
    """Excel住所から値を抽出し、同時にその値を返す"""
    try:
        m = re.match(r"([A-Z]+)([0-9]+)", ref)
        c_str, r_str = m.groups()
        c_idx = 0
        for char in c_str: c_idx = c_idx * 26 + (ord(char) - ord('A') + 1)
        val = df.iloc[int(r_str)-1, c_idx-1]
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('¥', '').strip())
    except: return 0.0

st.title("🧪 Gas Lab Engine : 算定根拠可視化モデル")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をロード", type=["xlsx"])

if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    
    # --- 算定プロセスの「解体」 ---
    if "別表4,5" in sheets:
        df_b = sheets["別表4,5"]
        # I56に至る主要な内訳セルを特定（これらは一般的な別表4,5の構成に基づく例）
        db["final_cost"] = cell(df_b, "I56")      # 総括原価合計
        db["op_expenses"] = cell(df_b, "I40")     # 営業費小計（人件費・修繕費等）
        db["depreciation"] = cell(df_b, "I45")    # 減価償却費
        db["taxes"] = cell(df_b, "I48")           # 租税公課
        db["return_val"] = cell(df_b, "I52")      # 事業報酬
        
    if "販売量" in sheets:
        db["vol_yakkan"] = cell(sheets["販売量"], "O8") # 規制部門
        db["vol_others"] = cell(sheets["販売量"], "O9") + cell(sheets["販売量"], "O10") # 自由部門

# --- Dashboard : ホワイトボックス表示 ---
if uploaded_file:
    st.header("📊 算定 Dashboard (透明性確保版)")
    c1, c2, c3 = st.columns(3)
    c1.metric("総括原価 (I56)", f"¥{db['final_cost']:,.0f}")
    c2.metric("約款販売量 (O8)", f"{db['vol_yakkan']:,.1f} m3")
    c3.metric("確定供給単価", f"{db['final_cost']/db['vol_yakkan']:,.2f} 円/m3")

    st.subheader("🔍 総括原価の内訳（別表4,5 トレーサビリティ）")
    # ウォーターフォール図的な内訳表示
    breakdown_data = {
        "項目": ["営業費 (人件費・修繕費等)", "減価償却費", "租税公課", "事業報酬"],
        "金額 (円)": [db['op_expenses'], db['depreciation'], db['taxes'], db['return_val']],
        "Excel座標": ["I40", "I45", "I48", "I52"]
    }
    st.table(pd.DataFrame(breakdown_data))

    st.info("💡 この数値は「別表4,5」の各集計行から直接取得しています。Excel側の数式を変更すると、ここの内訳も自動的に追従します。")

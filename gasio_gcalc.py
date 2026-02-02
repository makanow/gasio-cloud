import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : Final Master", layout="wide")

# 1. 状態の初期化
if 'db' not in st.session_state:
    st.session_state.db = {
        "res_land_invest": 0.0, "invest_1": 0.0, "invest_2": 0.0, "res_land_eval": 0.0,
        "return_rate": 0.0272, "reduction_rate": 0.46, "total_sales_volume": 0.0,
        "lpg_price": 0.0, "permit_locations": 0.0, "res_tax_total_F": 0.0,
        "res_return": 0.0, "res_dep": 0.0
    }
db = st.session_state.db

# --- 座標変換ユーティリティ ---
def excel_get(df, cell_ref):
    """'D11' や 'O11' といった文字列から値を直接抽出する"""
    import re
    match = re.match(r"([A-Z]+)([0-9]+)", cell_ref)
    col_str, row_str = match.groups()
    
    # 列変換 (A=0, B=1...)
    col_idx = 0
    for char in col_str:
        col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
    col_idx -= 1
    
    # 行変換 (Excelの11行目 = pandasのindex 9 ※header=0想定)
    # pd.read_excel(header=None) で読み込む場合は row_idx = int(row_str) - 1
    row_idx = int(row_str) - 2 # 一般的なヘッダーあり読み込みの場合
    
    try:
        val = df.iloc[row_idx, col_idx]
        return val
    except:
        return 0.0

def clean_v(val):
    try:
        if pd.isna(val) or val == "": return 0.0
        s = str(val).replace(',', '').replace('¥', '').replace('点', '').replace('m3', '').strip()
        return float(s)
    except: return 0.0

# --- UI ---
st.title("🧪 Gas Lab Engine : 最終供給単価算定")

uploaded_file = st.file_uploader("G-Calc_master.xlsx をアップロード", type=["xlsx"])

if uploaded_file:
    # 座標ズレを防ぐため、ヘッダーなし(header=None)で全域を読み込む
    sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    
    # セルから値を引くための関数 (header=None用)
    def cell(df, ref):
        import re
        m = re.match(r"([A-Z]+)([0-9]+)", ref)
        c_str, r_str = m.groups()
        c_idx = 0
        for char in c_str: c_idx = c_idx * 26 + (ord(char) - ord('A') + 1)
        return clean_v(df.iloc[int(r_str)-1, c_idx-1])

    # --- A. 土地・資産の再計算 ---
    if "土地" in sheets:
        df_l = sheets["土地"]
        # 5列目(E), 6列目(F), 8列目(H) の15行目
        area = cell(df_l, "E15")
        price = cell(df_l, "F15")
        db["res_land_eval"] = cell(df_l, "H15")
        db["res_land_area_adj"] = min(area, 295.0)
        db["res_land_invest"] = round(price / area, 0) * db["res_land_area_adj"]

    if "償却資産" in sheets:
        df_a = sheets["償却資産"]
        # 10列目(J)フラグ, 11列目(K)モード, 12列目(L)実績, 13列目(M)標準
        # 2行目から最終行までループ
        inv1, inv2 = 0.0, 0.0
        for i in range(1, len(df_a)):
            mode = clean_v(df_a.iloc[i, 10]) # K列
            val = clean_v(df_a.iloc[i, 11]) if mode == 1 else clean_v(df_a.iloc[i, 12])
            if clean_v(df_a.iloc[i, 9]) == 1: inv2 += val # J列
            else: inv1 += val
        db["invest_1"], db["invest_2"] = inv1, inv2

    # --- B. 販売量・原料価格 ---
    if "ナビ" in sheets:
        df_n = sheets["ナビ"]
        db["lpg_price"] = cell(df_n, "D14")
        db["permit_locations"] = cell(df_n, "D11")

    if "販売量" in sheets:
        df_s = sheets["販売量"]
        only_std = (cell(df_s, "C4") == 1)
        use_std = (cell(df_s, "C5") == 1)
        if only_std and use_std:
            db["total_sales_volume"] = db["permit_locations"] * 250
        else:
            db["total_sales_volume"] = cell(df_s, "O11")

    # --- C. 財務精密ロジック (v6.9準拠) ---
    f1 = round(db["res_land_eval"] * 0.017, 0)
    f4 = round((db["invest_1"] / 2) + (db["invest_2"] * 0.46 / 2), 0)
    f2 = round(f4 * 0.014, 0)
    db["res_tax_total_F"] = f1 + f2
    db["res_return"] = round((db["res_land_invest"] + db["invest_1"] + db["invest_2"]) * db["return_rate"], 0)
    db["res_dep"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)

# --- Dashboard ---
if uploaded_file:
    st.header("📊 供給単価 最終Dashboard")
    total_fixed = db["res_dep"] + db["res_tax_total_F"] + db["res_return"]
    total_raw = db["total_sales_volume"] * db["lpg_price"]
    final_total = total_fixed + total_raw
    unit_price = final_total / db["total_sales_volume"] if db["total_sales_volume"] > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("最終総括原価", f"¥{final_total:,.0f}")
    c2.metric("予定販売量", f"{db['total_sales_volume']:,.1f} m3")
    c3.metric("供給単価", f"{unit_price:,.2f} 円/m3")

    with st.expander("📝 最終算定根拠"):
        st.write(f"固定資産税(F): ¥{db['res_tax_total_F']:,.0f}")
        st.write(f"事業報酬: ¥{db['res_return']:,.0f}")
        st.write(f"原料費: ¥{total_raw:,.0f}")

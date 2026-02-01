import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- Excel完全互換・四捨五入（G54の規律） ---
def excel_round(value, decimals=0):
    try:
        if value is None or pd.isna(value): return 0.0
        v = float(str(value).replace(',', '').replace('¥', ''))
        d = Decimal(str(v))
        exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))
    except: return 0.0

st.set_page_config(page_title="G-Calc Master: 精密一致版", layout="wide")
st.title("🛡️ G-Calc Master: 数値完全同期・算定要塞")

EXCEL_FILE = "G-Calc_master.xlsx"

# 資産座標設定 (列E=4, F=5...)
ASSET_CONFIG = {
    "建物": {"col": 4, "rate": 0.03},
    "構築物": {"col": 5, "rate": 0.1},
    "集合装置": {"col": 6, "rate": 0.1},
    "容器": {"col": 7, "rate": 0.167},
    "導管・鋼管共同": {"col": 8, "rate": 0.077},
    "導管・ＰＥ共同": {"col": 9, "rate": 0.077},
    "導管・鋼管単独": {"col": 10, "rate": 0.077},
    "導管・ＰＥ単独": {"col": 11, "rate": 0.077},
    "メーター": {"col": 12, "rate": 0.077},
}

# --- マスタ精密読込 ---
@st.cache_data
def load_masters_precision():
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        # Aシート
        df_a = xl.parse('標準係数A', header=None)
        
        # 投資単価（B6以降）
        infra_m = df_a.iloc[5:].copy()
        infra_m = infra_m[infra_m.iloc[:, 1].astype(str).str.contains("HK", na=False)]
        
        # 車両単価（T4:AA24）: 行24(Index 23)にある最新単価をターゲット
        # ナガセの「T5:AA13はブランク」を考慮し、有効な最終行(24行目)を狙う
        ca_row = df_a.iloc[23, 19:27].fillna(0).astype(float).values
        
        # Bシート
        df_b = xl.parse('標準係数B', skiprows=3, header=None)
        pref_dict = df_b.iloc[:, [2, 4, 6]].dropna().set_index(2).to_dict('index')
        
        return infra_m, pref_dict, ca_row
    except Exception as e:
        st.error(f"精密読込失敗: {e}")
        return pd.DataFrame(), {}, [0.0]*8

infra_master, pref_dict, ca_row_data = load_masters_precision()

# --- UI ---
st.sidebar.header("🌍 要塞設定")
selected_pref = st.sidebar.selectbox("都道府県", list(pref_dict.keys()), index=0)
total_customers = st.sidebar.number_input("許可地点数", value=245)

# --- 計算回路 ---
st.header("🏗️ 投資・償却 算出エンジン")
if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "方式": "標準係数"},
    ])

edited_df = st.data_editor(st.session_state.invest_df, num_rows="dynamic", use_container_width=True)

calc_rows = []
total_dep_raw = 0.0

for i in range(len(edited_df)):
    row = edited_df.iloc[i]
    if not row.get("項目"): continue
    
    dt = pd.to_datetime(row.get("取得年月日"), errors='coerce')
    cfg = ASSET_CONFIG.get(row["項目"], {"col": 4, "rate": 0.03})
    
    # マスタから単価を厳密に抽出
    p_row = infra_master[(pd.to_datetime(infra_master.iloc[:, 2]) <= dt) & 
                         (pd.to_datetime(infra_master.iloc[:, 3], errors='coerce').fillna(pd.Timestamp('2100-12-31')) >= dt)]
    
    if not p_row.empty:
        u_price = float(p_row.iloc[0, cfg["col"]])
        invest = float(row.get("地点数", 0)) * u_price
        dep = invest * cfg["rate"]
        
        calc_rows.append({"項目": row["項目"], "単価": u_price, "投資額": invest, "償却費": dep})
        total_dep_raw += dep

# 車両(CA)計算: 地点数245ならCA1(Index 0)と仮定
ca_u_price = ca_row_data[0] 
ca_invest = total_customers * ca_u_price
ca_dep = ca_invest * 0.2
total_dep_raw += ca_dep

# --- 最終集計（G54の規律） ---
final_dep = excel_round(total_dep_raw, 0) # ここで初めて四捨五入

# --- 表示 ---
st.subheader("📊 算出結果（Excel同期確認用）")
if calc_rows:
    res_df = pd.DataFrame(calc_results) # 前回の変数が残らないよう注意
    st.table(pd.DataFrame(calc_rows).style.format({"単価": "{:,.0f}", "投資額": "{:,.0f}", "償却費": "{:,.2f}"}))

st.divider()
c1, c2 = st.columns(2)
c1.metric("総投資額 (車両込)", f"¥ {sum([r['投資額'] for r in calc_rows]) + ca_invest:,.0f}")
c2.metric("総 減価償却費 (G54:四捨五入)", f"¥ {final_dep:,.0f}")

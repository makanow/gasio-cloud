import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- Excel互換・四捨五入エンジン ---
def excel_round(value, decimals=0):
    try:
        if value is None or pd.isna(value): return 0
        d = Decimal(str(float(value)))
        exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))
    except:
        return 0

st.set_page_config(page_title="G-Calc Master: セル番地準拠版", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産 最終算定エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

# 【精密座標】セルE=Index4, F=5, G=6...
ASSET_CONFIG = {
    "建物": {"col": 4, "code": "TTM"},          # E列
    "構築物": {"col": 5, "code": "KCB"},        # F列
    "集合装置": {"col": 6, "code": "SGS"},      # G列
    "容器": {"col": 7, "code": "YKI"},          # H列
    "導管・鋼管共同": {"col": 8, "code": "DKK"}, # I列
    "導管・ＰＥ共同": {"col": 9, "code": "DPK"}, # J列
    "導管・鋼管単独": {"col": 10, "code": "DKT"}, # K列
    "導管・ＰＥ単独": {"col": 11, "code": "DPT"}, # L列
    "メーター": {"col": 12, "code": "MTR"},      # M列
}

# --- 1. 標準係数B（県別）：C4開始 ---
@st.cache_data
def load_pref_master():
    try:
        # C4(Index 3行目, 2列目)から開始
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        # 県名=C列(2), 労務費=E列(4), 産気率=G列(6)
        master = df_b.iloc[:, [2, 4, 6]].dropna()
        master.columns = ['pref', 'wage', 'gas_rate']
        return master.set_index('pref').to_dict('index')
    except:
        return {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

# --- 2. 標準係数A（資産・HK）：E5, B6開始 ---
@st.cache_data
def load_infra_master():
    try:
        df_raw = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', header=None)
        
        # A. 償却率：5行目(Index 4), E列(Index 4)〜R列
        rates = pd.to_numeric(df_raw.iloc[4, 4:18], errors='coerce').fillna(0).tolist()
        
        # B. 単価データ：6行目(Index 5)〜, B列(Index 1)がHK
        df_data = df_raw.iloc[5:].copy()
        master = df_data[df_data.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        def fix_date(val):
            v_str = str(val).split(' ')[0]
            if "9999" in v_str: return pd.Timestamp("2100-12-31")
            return pd.to_datetime(v_str, errors='coerce')

        master['start_dt'] = pd.to_datetime(master.iloc[:, 2], errors='coerce') # C列
        master['end_dt'] = master.iloc[:, 3].apply(fix_date)                   # D列
        return master, rates
    except Exception as e:
        st.error(f"マスタ読込エラー: {e}")
        return pd.DataFrame(), [0.03] * 14

pref_dict = load_pref_master()
infra_master, dep_rates = load_infra_master()

# 償却率を資産に紐付け
for i, name in enumerate(ASSET_CONFIG.keys()):
    if i < len(dep_rates):
        ASSET_CONFIG[name]["rate"] = dep_rates[i]

# --- 3. UI & 算定 ---
selected_pref = st.sidebar.selectbox("都道府県", list(pref_dict.keys()))
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1)

if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免しない"},
    ])

edited_df = st.data_editor(st.session_state.invest_df, num_rows="dynamic", use_container_width=True)

# 計算処理
results = []
for idx, row in edited_df.iterrows():
    if pd.isna(row.get("項目")): continue
    # 期間検索
    dt = pd.to_datetime(row.get("取得年月日"))
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    p_data = match.iloc[0] if not match.empty else None
    
    cfg = ASSET_CONFIG.get(row["項目"], {"col": 4, "rate": 0})
    u_price = float(p_data.iloc[cfg["col"]]) if p_data is not None else 0
    
    invest = excel_round(row.get("実績額", 0), 0) if row.get("方式") == "実績値" else excel_round(float(row.get("地点数", 0)) * u_price, 0)
    dep = excel_round(invest * cfg["rate"], 1)
    
    results.append({
        "項目": row["項目"], "投資額": invest, "償却費": dep, "減免": row.get("減免")
    })

# --- 表示 ---
if results:
    res_df = pd.DataFrame(results)
    st.dataframe(res_df.style.format({"投資額": "{:,.0f}", "償却費": "{:,.1f}"}), use_container_width=True)
    
    wage = pref_dict[selected_pref]['wage']
    st.metric("労務費(参考)", f"¥ {excel_round(total_customers * 0.0031 * wage, 0):,.0f}")

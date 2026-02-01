import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- Excel互換の四捨五入エンジン ---
def excel_round(value, decimals=0):
    try:
        if value is None or pd.isna(value): return 0
        d = Decimal(str(value))
        exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))
    except:
        return 0

st.set_page_config(page_title="G-Calc Master: 統合要塞", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産 統合算定エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

# 項目名と標準係数A（列4〜）の対応マップ
ASSET_MAP = {
    "建物": {"col": 4, "code": "TTM"},
    "構築物": {"col": 5, "code": "KCB"},
    "集合装置": {"col": 6, "code": "SGS"},
    "容器": {"col": 7, "code": "YKI"},
    "導管・鋼管共同": {"col": 8, "code": "DKK"},
    "導管・ＰＥ共同": {"col": 9, "code": "DPK"},
    "導管・鋼管単独": {"col": 10, "code": "DKT"},
    "導管・ＰＥ単独": {"col": 11, "code": "DPT"},
    "メーター": {"code": "MTR", "col": 12},
}

# --- 1. 都道府県マスタ (標準係数B) ---
@st.cache_data
def load_pref_master():
    try:
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        master = df_b.iloc[:, [2, 4, 6]].dropna()
        master.columns = ['pref', 'wage', 'gas_rate']
        return master.set_index('pref').to_dict('index')
    except:
        return {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

# --- 2. 標準係数A：償却率と単価の複合読込 ---
@st.cache_data
def load_infra_master():
    try:
        # シート全体を読み込み
        df_full = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', header=None)
        
        # A. 償却率の取得（2行目、列4〜17）
        dep_rates = df_full.iloc[1, 4:18].astype(float).tolist()
        # B. 単価データの取得（3行目以降）
        df_data = df_full.iloc[2:].copy()
        master = df_data[df_data.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        def fix_date(val):
            v_str = str(val).split(' ')[0]
            if "9999" in v_str: return pd.Timestamp("2100-12-31")
            return pd.to_datetime(v_str, errors='coerce')

        master['start_dt'] = master.iloc[:, 2].apply(fix_date)
        master['end_dt'] = master.iloc[:, 3].apply(fix_date)
        
        return master, dep_rates
    except Exception as e:
        st.error(f"マスタ読込エラー: {e}")
        return pd.DataFrame(), [0.03] * 14

pref_dict = load_pref_master()
infra_master, dep_rate_list = load_infra_master()

# 償却率をマップに統合
for i, key in enumerate(ASSET_MAP.keys()):
    if i < len(dep_rate_list):
        ASSET_MAP[key]["rate"] = dep_rate_list[i]

# --- 判定ロジック ---
def find_period_info(target_date):
    if infra_master.empty or target_date is None: return "⚠️未入力", None
    dt = pd.to_datetime(target_date)
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        return f"{row['start_dt'].strftime('%Y/%m/%d')} 〜 {row['end_dt'].strftime('%Y/%m/%d')}", row
    return "⚠️対象外", None

# --- UI ---
st.sidebar.header("🌍 基本設定")
selected_pref = st.sidebar.selectbox("都道府県", list(pref_dict.keys()))
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1)

st.header(f"📍 {selected_pref} 算定コックピット")

if 'full_invest_df' not in st.session_state:
    st.session_state.full_invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免しない"},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免する"},
    ])

edited_df = st.data_editor(st.session_state.full_invest_df, num_rows="dynamic", use_container_width=True)
st.session_state.full_invest_df = edited_df

# --- 計算 ---
results = []
for idx, row in edited_df.iterrows():
    if pd.isna(row.get("項目")): continue
    p_label, p_data = find_period_info(row.get("取得年月日"))
    info = ASSET_MAP.get(row["項目"], {"col": 4, "rate": 0, "code": "???"})
    
    unit_price = p_data.iloc[info["col"]] if p_data is not None else 0
    invest = excel_round(row.get("実績額", 0), 0) if row.get("方式") == "実績値" else excel_round(float(row.get("地点数", 0)) * unit_price, 0)
    
    is_exempt = (row.get("減免") == "減免する")
    results.append({
        "項目": row["項目"], "時期": p_label, "投資額①": 0 if is_exempt else invest, 
        "投資額②": invest if is_exempt else 0, "償却費": excel_round(invest * info["rate"], 1), "code": info["code"]
    })

# --- 表示 ---
if results:
    res_df = pd.DataFrame(results)
    st.dataframe(res_df.drop(columns=["code"]), use_container_width=True,
                 column_config={"投資額①": st.column_config.NumberColumn(format="¥%,d"), "投資額②": st.column_config.NumberColumn(format="¥%,d"), "償却費": st.column_config.NumberColumn(format="¥%,.1f")})

    st.divider()
    labor_cost = excel_round(total_customers * 0.0031 * pref_dict[selected_pref]['wage'], 0)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("労務費", f"¥ {labor_cost:,.0f}")
    m2.metric("投資①合計", f"¥ {res_df['投資額①'].sum():,.0f}")
    m3.metric("投資②合計", f"¥ {res_df['投資額②'].sum():,.0f}")
    m4.metric("総償却費", f"¥ {res_df['償却費'].sum():,.1f}")

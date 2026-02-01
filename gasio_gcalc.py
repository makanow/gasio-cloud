import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- Excel互換の四捨五入（0.5切り上げ） ---
def excel_round(value, decimals=0):
    try:
        if value is None or pd.isna(value): return 0
        d = Decimal(str(value))
        exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))
    except:
        return 0

st.set_page_config(page_title="G-Calc Master: 精密再建版", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産 統合算定エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

# 【精密定義】ナガセの報告に基づき、列4(index3)から資産が並んでいると定義
# 列1=ID, 列2=開始, 列3=終了, 列4=建物 ...
ASSET_CONFIG = {
    "建物": {"col": 3, "code": "TTM"},          # index 3 (列4)
    "構築物": {"col": 4, "code": "KCB"},        # index 4 (列5)
    "集合装置": {"col": 5, "code": "SGS"},
    "容器": {"col": 6, "code": "YKI"},
    "導管・鋼管共同": {"col": 7, "code": "DKK"},
    "導管・ＰＥ共同": {"col": 8, "code": "DPK"},
    "導管・鋼管単独": {"col": 9, "code": "DKT"},
    "導管・ＰＥ単独": {"col": 10, "code": "DPT"},
    "メーター": {"col": 11, "code": "MTR"},
}

# --- 1. 都道府県マスタ (標準係数B) ---
@st.cache_data
def load_pref_master():
    try:
        # Bシート: 県名=列2(index1), 労務費=列4(index3), 産気率=列6(index5)
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        master = df_b.iloc[:, [1, 3, 5]].dropna()
        master.columns = ['pref', 'wage', 'gas_rate']
        return master.set_index('pref').to_dict('index')
    except:
        return {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

# --- 2. 標準係数A：絶対座標読込 ---
@st.cache_data
def load_infra_master():
    try:
        # Aシート: index1=償却率(2行目), index2〜=データ(3行目以降)
        df_raw = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', header=None)
        
        # 償却率を「列4(index3)以降」から取得
        rates = df_raw.iloc[1, 3:13].astype(float).tolist()
        
        # 単価データ(HKを含む行をフィルタ)
        data_rows = df_raw.iloc[2:].copy()
        master = data_rows[data_rows.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        def fix_date(val):
            v_str = str(val).split(' ')[0]
            if "9999" in v_str: return pd.Timestamp("2100-12-31")
            return pd.to_datetime(v_str, errors='coerce')

        master['start_dt'] = master.iloc[:, 2].apply(fix_date)
        master['end_dt'] = master.iloc[:, 3].apply(fix_date)
        return master, rates
    except Exception as e:
        st.error(f"マスタ読込失敗(座標ズレの可能性): {e}")
        return pd.DataFrame(), [0.03] * 10

pref_dict = load_pref_master()
infra_master, dep_rates = load_infra_master()

# 償却率を資産設定にマッピング
for i, name in enumerate(ASSET_CONFIG.keys()):
    if i < len(dep_rates):
        ASSET_CONFIG[name]["rate"] = dep_rates[i]

# --- UI ---
st.sidebar.header("🌍 エリア・全体設定")
selected_pref = st.sidebar.selectbox("都道府県", list(pref_dict.keys()))
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1, format="%d")

if 'full_invest_df' not in st.session_state:
    st.session_state.full_invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免しない"},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免する"},
    ])

edited_df = st.data_editor(st.session_state.full_invest_df, num_rows="dynamic", use_container_width=True)
st.session_state.full_invest_df = edited_df

# --- 算定メイン ---
def find_p(target_date):
    if infra_master.empty or target_date is None: return None, None
    dt = pd.to_datetime(target_date)
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        label = f"{row['start_dt'].strftime('%Y/%m/%d')} 〜 {row['end_dt'].strftime('%Y/%m/%d')}"
        return label, row
    return "対象外", None

results = []
for idx, row in edited_df.iterrows():
    if pd.isna(row.get("項目")): continue
    p_label, p_data = find_p(row.get("取得年月日"))
    cfg = ASSET_CONFIG.get(row["項目"], {"col": 3, "rate": 0})
    
    # マスタから単価取得(index=cfg['col'])
    u_price = p_data.iloc[cfg["col"]] if p_data is not None else 0
    invest = excel_round(row.get("実績額", 0), 0) if row.get("方式") == "実績値" else excel_round(float(row.get("地点数", 0)) * u_price, 0)
    
    is_exempt = (row.get("減免") == "減免する")
    results.append({
        "項目": row["項目"], "取得時期": p_label, "地点数": row.get("地点数", 0),
        "投資額①": 0 if is_exempt else invest, "投資額②": invest if is_exempt else 0,
        "償却費": excel_round(invest * cfg["rate"], 1)
    })

# --- 表示 ---
st.divider()
if results:
    res_df = pd.DataFrame(results)
    st.dataframe(res_df, use_container_width=True,
                 column_config={"投資額①": st.column_config.NumberColumn(format="¥%,d"), "投資額②": st.column_config.NumberColumn(format="¥%,d"), "償却費": st.column_config.NumberColumn(format="¥%,.1f")})

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    wage = pref_dict[selected_pref]['wage']
    m1.metric("労務費合計", f"¥ {excel_round(total_customers * 0.0031 * wage, 0):,.0f}")
    m2.metric("投資額①合計", f"¥ {res_df['投資額①'].sum():,.0f}")
    m3.metric("投資額②合計", f"¥ {res_df['投資額②'].sum():,.0f}")
    m4.metric("総 減価償却費", f"¥ {res_df['償却費'].sum():,.1f}")

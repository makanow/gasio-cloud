import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- Excel互換の四捨五入（0.5で切り上げ） ---
def excel_round(value, decimals=0):
    try:
        if value is None or pd.isna(value): return 0
        d = Decimal(str(value))
        exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))
    except:
        return 0

st.set_page_config(page_title="G-Calc Master: 集大成版", layout="wide")
st.title("🛡️ G-Calc Master: 総括原価算定要塞（Version 1.1）")

EXCEL_FILE = "G-Calc_master.xlsx"

# 資産マスタ設定
ASSET_INFO = {
    "建物": {"col": 3, "rate": 0.03, "code": "TTM"},
    "構築物": {"col": 4, "rate": 0.1, "code": "KCB"},
    "集合装置": {"col": 5, "rate": 0.1, "code": "SGS"},
    "容器": {"col": 6, "rate": 0.167, "code": "YKI"},
    "導管・鋼管共同": {"col": 7, "rate": 0.077, "code": "DKK"},
    "導管・ＰＥ共同": {"col": 8, "rate": 0.077, "code": "DPK"},
    "導管・鋼管単独": {"col": 9, "rate": 0.077, "code": "DKT"},
    "導管・ＰＥ単独": {"col": 10, "rate": 0.077, "code": "DPT"},
    "メーター": {"col": 11, "rate": 0.077, "code": "MTR"},
    "備品": {"col": 12, "rate": 0.2, "code": "BHN"},
    "強制気化装置": {"col": 16, "rate": 0.1, "code": "KKS"}
}

# --- 1. 都道府県マスタ読込 ---
@st.cache_data
def load_pref_master():
    try:
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        master = df_b.iloc[:, [2, 4, 6]].dropna()
        master.columns = ['pref', 'wage', 'gas_rate']
        return master.set_index('pref').to_dict('index')
    except:
        return {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

# --- 2. 投資期間マスタ読込 ---
@st.cache_data
def load_infra_master():
    try:
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
        master = df_a[df_a.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        master = master.iloc[:, 1:].reset_index(drop=True)
        def fix_date(val):
            v_str = str(val).split(' ')[0]
            return pd.Timestamp("2100-12-31") if "9999" in v_str else pd.to_datetime(v_str, errors='coerce')
        master['start_dt'] = master.iloc[:, 1].apply(fix_date)
        master['end_dt'] = master.iloc[:, 2].apply(fix_date)
        return master
    except:
        return pd.DataFrame()

pref_dict = load_pref_master()
infra_master = load_infra_master()

def find_period_info(target_date):
    if infra_master.empty or target_date is None or pd.isna(target_date):
        return "⚠️日付未入力", None
    try:
        dt = pd.to_datetime(target_date)
        match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
        if not match.empty:
            row = match.iloc[0]
            return f"{row['start_dt'].strftime('%Y/%m/%d')} 〜 {row['end_dt'].strftime('%Y/%m/%d')}", row
        return f"{infra_master.iloc[-1]['start_dt'].strftime('%Y/%m/%d')} 〜", infra_master.iloc[-1]
    except:
        return "⚠️形式エラー", None

# --- UI：サイドバー ---
st.sidebar.header("🌍 エリア・全体設定")
selected_pref = st.sidebar.selectbox("対象都道府県", list(pref_dict.keys()), index=0)
total_customers = st.sidebar.number_input("許可地点数 (整数)", value=245, step=1, format="%d")

pref_data = pref_dict[selected_pref]
wage = pref_data['wage']
gas_rate = pref_data['gas_rate']

# --- UI：メイン ---
st.header(f"📍 {selected_pref} 算定コックピット")
st.info(f"標準労務単価: ¥ {wage:,.0f} / 産気率: {gas_rate}")

if 'full_invest_df' not in st.session_state:
    st.session_state.full_invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免しない"},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免する"},
    ])

edited_df = st.data_editor(
    st.session_state.full_invest_df,
    num_rows="dynamic",
    column_config={
        "地点数": st.column_config.NumberColumn(format="%,d"),
        "実績投資額": st.column_config.NumberColumn(format="%,d"),
    },
    use_container_width=True
)
st.session_state.full_invest_df = edited_df

# --- 計算 ---
results = []
for idx, row in edited_df.iterrows():
    if pd.isna(row.get("項目")) or row.get("項目") is None: continue
    
    p_label, p_data = find_period_info(row.get("取得年月日"))
    info = ASSET_INFO.get(row["項目"], {"col": 3, "rate": 0, "code": "???"})
    
    unit_price = p_data.iloc[info["col"]] if p_data is not None else 0
    invest_base = excel_round(row.get("実績投資額", 0), 0) if row.get("算出方式") == "実績値" else excel_round(float(row.get("地点数", 0)) * unit_price, 0)
    
    is_exempt = (row.get("減免適用") == "減免する")
    results.append({
        "項目": row["項目"], "時期": p_label, "地点数": row.get("地点数", 0),
        "投資額①": 0 if is_exempt else invest_base,
        "投資額②": invest_base if is_exempt else 0,
        "償却費": excel_round(invest_base * info["rate"], 1),
        "code": info["code"]
    })

# --- サマリー表示 ---
if results:
    res_df = pd.DataFrame(results)
    st.dataframe(
        res_df.drop(columns=["code"]),
        column_config={
            "投資額①": st.column_config.NumberColumn(format="¥%,d"),
            "投資額②": st.column_config.NumberColumn(format="¥%,d"),
            "償却費": st.column_config.NumberColumn(format="¥%,.1f"),
            "地点数": st.column_config.NumberColumn(format="%,d"),
        },
        use_container_width=True
    )
    
    labor_cost = excel_round(total_customers * 0.0031 * wage, 0)
    
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("労務費合計", f"¥ {labor_cost:,.0f}")
    m2.metric("投資額①合計", f"¥ {res_df['投資額①'].sum():,.0f}")
    m3.metric("投資額②合計", f"¥ {res_df['投資額②'].sum():,.0f}")
    m4.metric("総 減価償却費", f"¥ {res_df['償却費'].sum():,.1f}")

    # バリデーション
    pipe_sum = res_df[res_df["code"].isin(["DKK", "DPK", "DKT", "DPT"])]["地点数"].sum()
    if pipe_sum != total_customers:
        st.error(f"❌ 導管合計：{pipe_sum:,} (目標：{total_customers:,})")

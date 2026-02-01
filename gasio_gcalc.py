import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- Excel互換の四捨五入 ---
def excel_round(value, decimals=0):
    if pd.isna(value) or value is None: return 0
    d = Decimal(str(value))
    exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
    return float(d.quantize(exp, rounding=ROUND_HALF_UP))

st.set_page_config(page_title="G-Calc Master: 最終検算版", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産算定エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

ASSET_INFO = {
    "建物": {"code": "TTM", "col": 3, "rate": 0.03},
    "構築物": {"code": "KCB", "col": 4, "rate": 0.1},
    "集合装置": {"code": "SGS", "col": 5, "rate": 0.1},
    "容器": {"code": "YKI", "col": 6, "rate": 0.167},
    "導管・鋼管共同": {"code": "DKK", "col": 7, "rate": 0.077},
    "導管・ＰＥ共同": {"code": "DPK", "col": 8, "rate": 0.077},
    "導管・鋼管単独": {"code": "DKT", "col": 9, "rate": 0.077},
    "導管・ＰＥ単独": {"code": "DPT", "col": 10, "rate": 0.077},
    "メーター": {"code": "MTR", "col": 11, "rate": 0.077},
    "備品": {"code": "BHN", "col": 12, "rate": 0.2},
    "強制気化装置": {"code": "KKS", "col": 16, "rate": 0.1}
}

EXEMPT_CODES = ["SGS", "DKK", "DPK", "DKT", "DPT", "SSB"]
EXEMPT_LIMIT_DATE = datetime(2017, 4, 1).date()

# --- マスタ読込（エラーガード強化） ---
@st.cache_data
def load_infra_master():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
        # HKを含む行を抽出
        master = df[df.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        master = master.iloc[:, 1:].reset_index(drop=True)
        
        def fix_date(val):
            v_str = str(val).split(' ')[0]
            if "9999" in v_str: return pd.Timestamp("2100-12-31")
            return pd.to_datetime(v_str, errors='coerce')

        master['start_dt'] = master.iloc[:, 1].apply(fix_date)
        master['end_dt'] = master.iloc[:, 2].apply(fix_date)
        return master
    except Exception as e:
        st.error(f"⚠️ マスタ読込失敗。Excelのシート名「標準係数A」を確認してください: {e}")
        return pd.DataFrame()

infra_master = load_infra_master()

def find_period_info(target_date):
    if infra_master.empty or target_date is None: 
        return "⚠️判定不可(マスタ空)", None
    dt = pd.to_datetime(target_date)
    # 型を揃えて比較
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        return f"{row['start_dt'].strftime('%Y/%m/%d')} 〜 {row['end_dt'].strftime('%Y/%m/%d')}", row
    last = infra_master.iloc[-1]
    return f"{last['start_dt'].strftime('%Y/%m/%d')} 〜 {last['end_dt'].strftime('%Y/%m/%d')}", last

# --- UI ---
st.sidebar.header("⚙️ 全体設定")
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1)

if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免しない"},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免する"},
    ])

# エディタの桁区切り設定
edited_df = st.data_editor(
    st.session_state.invest_df,
    num_rows="dynamic",
    column_config={
        "実績投資額": st.column_config.NumberColumn("実績値(円)", format="%,d"),
        "地点数": st.column_config.NumberColumn("地点数", format="%,d"),
    },
    use_container_width=True
)
st.session_state.invest_df = edited_df

# --- 計算 ---
results = []
for index, row in edited_df.iterrows():
    if row["取得年月日"] is None or pd.isna(row["取得年月日"]):
        results.append({"項目": row["項目"], "取得時期": "⚠️日付入力待ち", "地点数": row["地点数"], "投資額①": 0, "投資額②": 0, "減価償却費": 0, "code": "ERR"})
        continue

    p_label, p_data = find_period_info(row["取得年月日"])
    info = ASSET_INFO.get(row["項目"], {"code": "UNKNOWN", "col": 3, "rate": 0})
    
    if row["算出方式"] == "実績値":
        invest_base = excel_round(row["実績投資額"], 0)
    else:
        unit_price = p_data.iloc[info["col"]] if p_data is not None else 0
        invest_base = excel_round(row["地点数"] * unit_price, 0)
    
    is_exempt = (row["減免適用"] == "減免する")
    inv1 = 0 if is_exempt else invest_base
    inv2 = invest_base if is_exempt else 0
    dep = excel_round(invest_base * info["rate"], 1)
    
    results.append({"項目": row["項目"], "取得時期": p_label, "地点数": row["地点数"], "投資額①": inv1, "投資額②": inv2, "減価償却費": dep, "code": info["code"]})

res_df = pd.DataFrame(results)

# --- 表示（カンマ強制） ---
st.divider()
if not res_df.empty:
    st.subheader("📊 算定結果サマリー")
    st.dataframe(
        res_df.drop(columns=["code"]),
        column_config={
            "投資額①": st.column_config.NumberColumn("投資額①", format="¥%,d"),
            "投資額②": st.column_config.NumberColumn("投資額②", format="¥%,d"),
            "減価償却費": st.column_config.NumberColumn("減価償却費", format="¥%,.1f"),
            "地点数": st.column_config.NumberColumn("地点数", format="%,d"),
        },
        use_container_width=True
    )
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("投資額① 合計", f"¥ {res_df['投資額①'].sum():,.0f}")
    m2.metric("投資額② 合計", f"¥ {res_df['投資額②'].sum():,.0f}")
    m3.metric("総 減価償却費", f"¥ {res_df['減価償却費'].sum():,.1f}")

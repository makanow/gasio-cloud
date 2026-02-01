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

st.set_page_config(page_title="G-Calc Master: 最終修正版", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産算定エンジン（最終修正）")

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

# --- マスタ読込 ---
@st.cache_data
def load_infra_master():
    try:
        # Excel読み込み。データが存在しない場合の防御
        df = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
        # HK（期間ID）を含む行のみ抽出
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
        st.error(f"マスタ読込エラー: {e}")
        return pd.DataFrame()

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
        return "⚠️日付形式エラー", None

# --- UI ---
st.sidebar.header("⚙️ 設定")
total_customers = st.sidebar.number_input("許可地点数", value=245)

if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免しない"},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免する"},
    ])

# 編集用テーブル（カンマ区切り設定を強化）
edited_df = st.data_editor(
    st.session_state.invest_df,
    num_rows="dynamic",
    column_config={
        "地点数": st.column_config.NumberColumn(format="%,d"),
        "実績投資額": st.column_config.NumberColumn(format="%,d"),
    },
    use_container_width=True
)
st.session_state.invest_df = edited_df

# --- 計算（ガードを鉄壁に） ---
results = []
for idx, row in edited_df.iterrows():
    # 必須項目が欠落している行はスキップ
    if pd.isna(row.get("項目")) or row.get("項目") is None:
        continue
    
    p_label, p_data = find_period_info(row.get("取得年月日"))
    info = ASSET_INFO.get(row["項目"], {"col": 3, "rate": 0, "code": "???"})
    
    # 単価取得
    unit_price = 0
    if p_data is not None:
        try:
            unit_price = p_data.iloc[info["col"]]
        except:
            unit_price = 0

    # 投資額
    if row.get("算出方式") == "実績値":
        invest_base = excel_round(row.get("実績投資額", 0), 0)
    else:
        invest_base = excel_round(float(row.get("地点数", 0)) * unit_price, 0)
    
    is_exempt = (row.get("減免適用") == "減免する")
    inv1 = 0 if is_exempt else invest_base
    inv2 = invest_base if is_exempt else 0
    dep = excel_round(invest_base * info["rate"], 1)
    
    results.append({
        "項目": row["項目"], "時期": p_label, "地点数": row.get("地点数", 0),
        "投資額①": inv1, "投資額②": inv2, "償却費": dep, "code": info["code"]
    })

# --- 表示（最終サマリー） ---
st.divider()
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
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("有形固定資産 投資額①", f"¥ {res_df['投資額①'].sum():,.0f}")
    m2.metric("有形固定資産 投資額②", f"¥ {res_df['投資額②'].sum():,.0f}")
    m3.metric("総 減価償却費", f"¥ {res_df['償却費'].sum():,.1f}")

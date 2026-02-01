import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master: 実務完全版", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産算定エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

# 資産項目と標準係数Aの列位置、償却率（コードは減免判定に使用）
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
    "強制気化装置": {"code": "KKS", "col": 16, "rate": 0.1},
    "集合装置・バルク": {"code": "SSB", "col": 14, "rate": 0.1}
}

# 減免対象コード（ナガセのExcel数式に基づく）
EXEMPT_CODES = ["SGS", "DKK", "DPK", "DKT", "DPT", "SSB"]
EXEMPT_LIMIT_DATE = datetime(2017, 4, 1).date()

# ---------------------------------------------------------
# 2. マスタ読込と判定関数
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
        master = df[df.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        master = master.iloc[:, 1:].reset_index(drop=True)
        
        def fix_date(val):
            val_str = str(val).split(' ')[0]
            if "9999" in val_str: return pd.Timestamp("2100-12-31")
            return pd.to_datetime(val_str, errors='coerce')

        master['start_dt'] = master.iloc[:, 1].apply(fix_date)
        master['end_dt'] = master.iloc[:, 2].apply(fix_date)
        return master
    except Exception as e:
        st.error(f"マスタ読込失敗：{e}")
        return pd.DataFrame()

infra_master = load_infra_master()

def find_period_info(target_date):
    if infra_master.empty or target_date is None: 
        return "日付未入力", None
    
    dt = pd.to_datetime(target_date)
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        return f"{row['start_dt'].strftime('%Y/%m/%d')} 〜 {row['end_dt'].strftime('%Y/%m/%d')}", row
    last = infra_master.iloc[-1]
    return f"{last['start_dt'].strftime('%Y/%m/%d')} 〜 {last['end_dt'].strftime('%Y/%m/%d')}", last

# ---------------------------------------------------------
# 3. メインUI
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体設定")
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1, format="%d")

st.header("🏗️ 分散取得・償却資産エディタ")
st.caption("取得日と項目に基づき、固定資産税の減免対象を自動判定します。")

if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "メーター", "地点数": total_customers, "取得年月日": datetime(2020, 1, 1).date(), "算出方式": "標準係数", "実績投資額": 0},
    ])

edited_df = st.data_editor(
    st.session_state.invest_df,
    num_rows="dynamic",
    column_config={
        "項目": st.column_config.SelectboxColumn("項目", options=list(ASSET_INFO.keys())),
        "取得年月日": st.column_config.DateColumn("取得年月日"),
        "算出方式": st.column_config.SelectboxColumn("方式", options=["標準係数", "実績値"]),
        "実績投資額": st.column_config.NumberColumn("実績値(円)", format="%,d"),
    },
    use_container_width=True
)
st.session_state.invest_df = edited_df

# ---------------------------------------------------------
# 4. 計算ロジック（自動減免判定搭載）
# ---------------------------------------------------------
results = []
for index, row in edited_df.iterrows():
    if row["取得年月日"] is None or pd.isna(row["取得年月日"]):
        results.append({"項目": row["項目"], "取得時期": "⚠️日付入力待ち", "地点数": row["地点数"], "投資額①": 0, "投資額②": 0, "減免": "非対象", "減価償却費": 0, "code": "ERR"})
        continue

    p_label, p_data = find_period_info(row["取得年月日"])
    info = ASSET_INFO.get(row["項目"], {"code": "UNKNOWN", "col": 3, "rate": 0})
    
    # 投資額算出
    if row["算出方式"] == "実績値":
        invest_base = int(row["実績投資額"])
    else:
        unit_price = p_data.iloc[info["col"]] if p_data is not None else 0
        invest_base = round(row["地点数"] * unit_price)
    
    # 【ナガセの数式：減免自動判定】
    # IF(AND(取得日 <= 2017/4/1, 項目が対象グループ), 1, 0)
    is_exempt = (row["取得年月日"] <= EXEMPT_LIMIT_DATE) and (info["code"] in EXEMPT_CODES)
        
    inv1 = 0 if is_exempt else invest_base
    inv2 = invest_base if is_exempt else 0
    dep = invest_base * info["rate"]
    
    results.append({
        "項目": row["項目"], "取得時期": p_label, "地点数": row["地点数"], 
        "投資額①": inv1, "投資額②": inv2, "減免": "✅対象" if is_exempt else "－",
        "減価償却費": dep, "code": info["code"]
    })

res_df = pd.DataFrame(results)

# ---------------------------------------------------------
# 5. 表示
# ---------------------------------------------------------
st.divider()
if not res_df.empty:
    st.subheader("📊 算定結果サマリー")
    st.dataframe(
        res_df.drop(columns=["code"]),
        column_config={
            "投資額①": st.column_config.NumberColumn("投資額①(非減免)", format="¥%,d"),
            "投資額②": st.column_config.NumberColumn("

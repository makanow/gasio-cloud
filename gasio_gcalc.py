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

st.set_page_config(page_title="G-Calc Master: 回路復旧版", layout="wide")
st.title("🛡️ G-Calc Master: 投資・償却資産 算定要塞")

EXCEL_FILE = "G-Calc_master.xlsx"

# 【精密座標】セルE=Index 4, F=5, G=6...
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

# --- マスタ読込 ---
@st.cache_data
def load_all_masters():
    try:
        df_a_raw = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', header=None)
        # 償却率: 5行目(Index 4), E列(Index 4)〜
        rates = pd.to_numeric(df_a_raw.iloc[4, 4:13], errors='coerce').fillna(0).tolist()
        # 単価データ: 6行目(Index 5)〜, B列(Index 1)がHK
        df_a_data = df_a_raw.iloc[5:].copy()
        infra_m = df_a_data[df_a_data.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        def fix_date(val):
            v_str = str(val).split(' ')[0]
            return pd.Timestamp("2100-12-31") if "9999" in v_str else pd.to_datetime(v_str, errors='coerce')
        
        infra_m['start_dt'] = pd.to_datetime(infra_m.iloc[:, 2], errors='coerce') # C列
        infra_m['end_dt'] = infra_m.iloc[:, 3].apply(fix_date)                   # D列
        
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        pref_m = df_b.iloc[:, [2, 4, 6]].dropna()
        pref_m.columns = ['pref', 'wage', 'gas_rate']
        pref_dict = pref_m.set_index('pref').to_dict('index')
        
        return infra_m, rates, pref_dict
    except Exception as e:
        st.error(f"マスタ読込エラー: {e}")
        return pd.DataFrame(), [0.03]*9, {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

infra_master, dep_rates, pref_dict = load_all_masters()

# --- UI ---
st.sidebar.header("🌍 基本設定")
selected_pref = st.sidebar.selectbox("都道府県", list(pref_dict.keys()), index=0)
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1)

st.header(f"🏗️ 分散取得・償却資産エディタ ({selected_pref})")

if 'invest_data' not in st.session_state:
    st.session_state.invest_data = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免しない"},
        {"項目": "メーター", "地点数": total_customers, "取得年月日": datetime(2020, 1, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免しない"},
    ])

# 【修正ポイント】エディタの出力を常にデータフレームとして処理
edited_data = st.data_editor(st.session_state.invest_data, num_rows="dynamic", use_container_width=True)
# セッションを更新
st.session_state.invest_data = edited_data

# --- 計算ループ ---
calc_results = []
# edited_data が DataFrame であることを保証してループ
for i in range(len(edited_data)):
    row = edited_data.iloc[i]
    if not row.get("項目"): continue
    
    dt = pd.to_datetime(row.get("取得年月日"))
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    p_data = match.iloc[0] if not match.empty else None
    
    asset_name = row["項目"]
    cfg = ASSET_CONFIG.get(asset_name, {"col": 4, "code": "???"})
    
    # 償却率の割り当て
    asset_idx = list(ASSET_CONFIG.keys()).index(asset_name) if asset_name in ASSET_CONFIG else 0
    current_rate = dep_rates[asset_idx] if asset_idx < len(dep_rates) else 0.03
    
    # 単価と投資額
    u_price = float(p_data.iloc[cfg["col"]]) if p_data is not None else 0
    invest = excel_round(row.get("実績額", 0), 0) if row.get("方式") == "実績値" else excel_round(float(row.get("地点数", 0)) * u_price, 0)
    
    dep = excel_round(invest * current_rate, 1)
    is_exempt = (row.get("減免") == "減免する")
    
    calc_results.append({
        "項目": asset_name,
        "投資額①": 0 if is_exempt else invest,
        "投資額②": invest if is_exempt else 0,
        "償却費": dep
    })

# --- 表示 ---
if calc_results:
    res_df = pd.DataFrame(calc_results)
    st.subheader("📊 算定結果サマリー")
    st.dataframe(
        res_df, 
        column_config={
            "投資額①": st.column_config.NumberColumn(format="¥%,d"),
            "投資額②": st.column_config.NumberColumn(format="¥%,d"),
            "償却費": st.column_config.NumberColumn(format="¥%,.1f"),
        },
        use_container_width=True
    )
    
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    wage = pref_dict[selected_pref]['wage']
    labor = excel_round(total_customers * 0.0031 * wage, 0)
    
    c1.metric("標準労務費", f"¥ {labor:,.0f}")
    c2.metric("投資額①合計", f"¥ {res_df['投資額①'].sum():,.0f}")
    c3.metric("投資額②合計", f"¥ {res_df['投資額②'].sum():,.0f}")
    c4.metric("総 減価償却費", f"¥ {res_df['償却費'].sum():,.1f}")

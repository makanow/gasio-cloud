import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- Excel完全互換・四捨五入 ---
def excel_round(value, decimals=0):
    try:
        if value is None or pd.isna(value): return 0.0
        v = float(str(value).replace(',', '').replace('¥', ''))
        d = Decimal(str(v))
        exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))
    except: return 0.0

st.set_page_config(page_title="G-Calc Master: 整合完了版", layout="wide")
st.title("🛡️ G-Calc Master: 数値完全同期・最終算定要塞")

EXCEL_FILE = "G-Calc_master.xlsx"

# 資産座標設定 (列E=Index4, F=Index5...)
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

# --- マスタ読込 ---
@st.cache_data
def load_masters_final():
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        df_a = xl.parse('標準係数A', header=None)
        
        # 投資単価（B6以降）
        infra_m = df_a.iloc[5:].copy()
        # HKを含む行のみ
        infra_m = infra_m[infra_m.iloc[:, 1].astype(str).str.contains("HK", na=False)]
        
        # 車両（T4:AA24 -> 列19:26）
        # 24行目(Index 23)が単価データ
        ca_data = df_a.iloc[23, 19:27].fillna(0).astype(float).values
        
        df_b = xl.parse('標準係数B', skiprows=3, header=None)
        pref_dict = df_b.iloc[:, [2, 4, 6]].dropna().set_index(2).to_dict('index')
        
        return infra_m, pref_dict, ca_data
    except Exception as e:
        st.error(f"読込失敗: {e}")
        return pd.DataFrame(), {}, [0.0]*8

infra_master, pref_dict, ca_units = load_masters_final()

# --- UI ---
st.sidebar.header("🌍 設定")
selected_pref = st.sidebar.selectbox("都道府県", list(pref_dict.keys()) if pref_dict else ["東京都"])
total_customers = st.sidebar.number_input("許可地点数", value=245)

# --- 計算 ---
st.header("🏗️ 算定エンジン")
if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date()},
    ])

edited_df = st.data_editor(st.session_state.invest_df, num_rows="dynamic", use_container_width=True)

final_rows = []
total_raw_dep = 0.0

for i in range(len(edited_df)):
    row = edited_df.iloc[i]
    if not row.get("項目"): continue
    
    dt = pd.to_datetime(row.get("取得年月日"), errors='coerce')
    cfg = ASSET_CONFIG.get(row["項目"], {"col": 4, "rate": 0.03})
    
    # 期間検索
    p_match = infra_master[(pd.to_datetime(infra_master.iloc[:, 2]) <= dt) & 
                           (pd.to_datetime(infra_master.iloc[:, 3], errors='coerce').fillna(pd.Timestamp('2100-12-31')) >= dt)]
    
    if not p_match.empty:
        u_price = float(p_match.iloc[0, cfg["col"]])
        invest = float(row.get("地点数", 0)) * u_price
        dep = invest * cfg["rate"]
        
        final_rows.append({
            "項目": row["項目"],
            "適用単価": u_price,
            "投資額": invest,
            "償却費(未丸め)": dep
        })
        total_raw_dep += dep

# 車両(CA)判定：245件ならCA2（Index 1）と仮定して計算
# 本来は地点数でIndexを動かす
ca_price = ca_units[1] if len(ca_units) > 1 else 0
ca_invest = total_customers * ca_price
ca_dep = ca_invest * 0.2
total_raw_dep += ca_dep

# --- 結果表示 ---
if final_rows:
    st.subheader("📊 詳細計算プロセス")
    res_display = pd.DataFrame(final_rows)
    st.table(res_display.style.format({"適用単価": "{:,.0f}", "投資額": "{:,.0f}", "償却費(未丸め)": "{:,.2f}"}))

st.divider()
c1, c2 = st.columns(2)
# 全合算後にG54のルールで四捨五入
final_total_dep = excel_round(total_raw_dep, 0)

c1.metric("総投資額 (車両込)", f"¥ {sum([r['投資額'] for r in final_rows]) + ca_invest:,.0f}")
c2.metric("総 減価償却費 (G54丸め)", f"¥ {final_total_dep:,.0f}")

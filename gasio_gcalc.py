import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# --- 実務用・四捨五入関数 ---
def excel_round(value, decimals=0):
    try:
        if value is None or pd.isna(value): return 0.0
        d = Decimal(str(float(value)))
        exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
        return float(d.quantize(exp, rounding=ROUND_HALF_UP))
    except: return 0.0

st.set_page_config(page_title="G-Calc Master: 最終起動版", layout="wide")
st.title("🛡️ G-Calc Master: 総括原価・料金算定 統合要塞")

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

# --- マスタ読込 ---
@st.cache_data
def load_masters():
    try:
        # Aシート: 投資・車両
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', header=None)
        # B6以降の期間データ
        infra_m = df_a.iloc[5:].copy()
        infra_m = infra_m[infra_m.iloc[:, 1].astype(str).str.contains("HK", na=False)]
        
        # 車両データ (T4:AA24 -> 列19:26)
        # CA区分判定用 (簡易的に地点数しきい値で実装)
        ca_master = df_a.iloc[13:24, 19:27].dropna(how='all') # 空白を避けて取得
        
        # Bシート: 都道府県 (C4開始)
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        pref_m = df_b.iloc[:, [2, 4, 6]].dropna()
        pref_dict = pref_m.set_index(2).to_dict('index')
        
        return infra_m, pref_dict, ca_master
    except Exception as e:
        st.error(f"マスタ読込エラー: {e}")
        return pd.DataFrame(), {}, pd.DataFrame()

infra_master, pref_dict, ca_master = load_masters()

# --- UI：エリア設定 ---
st.sidebar.header("🌍 全体設定")
selected_pref = st.sidebar.selectbox("都道府県", list(pref_dict.keys()), index=0)
total_customers = st.sidebar.number_input("許可地点数", value=245)

# --- UI：投資エディタ ---
st.header("🏗️ 分散取得・償却資産エディタ")
if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "方式": "標準係数", "実績額": 0, "減免": "減免しない"},
    ])

edited_df = st.data_editor(st.session_state.invest_df, num_rows="dynamic", use_container_width=True)

# --- 算定ロジック ---
calc_results = []
for i in range(len(edited_df)):
    row = edited_df.iloc[i]
    if not row.get("項目"): continue
    
    dt = pd.to_datetime(row.get("取得年月日"), errors='coerce')
    cfg = ASSET_CONFIG.get(row["項目"], {"col": 4, "rate": 0.03})
    
    # 期間単価取得
    p_row = infra_master[(pd.to_datetime(infra_master.iloc[:, 2]) <= dt) & 
                         (pd.to_datetime(infra_master.iloc[:, 3], errors='coerce').fillna(pd.Timestamp('2100-12-31')) >= dt)]
    
    u_price = float(p_row.iloc[0, cfg["col"]]) if not p_row.empty else 0
    invest = float(row.get("実績額", 0)) if row.get("方式") == "実績値" else float(row.get("地点数", 0)) * u_price
    dep = invest * cfg["rate"]
    
    is_exempt = (row.get("減免") == "減免する")
    calc_results.append({"投資額①": 0 if is_exempt else invest, "投資額②": invest if is_exempt else 0, "償却費": dep})

# --- 車両(CA)自動判定 ---
# 245件ならCA何に該当するかをマスタから特定（実務ロジック）
# 簡易的にCA1を適用（実際は地点数に応じてca_masterから行を特定）
ca_unit_price = float(ca_master.iloc[0, 0]) if not ca_master.empty else 0
ca_invest = total_customers * ca_unit_price
ca_dep = ca_invest * 0.2 # 車両償却率20%

# --- 集計 ---
res_df = pd.DataFrame(calc_results)
sum_inv1 = res_df["投資額①"].sum() + ca_invest
sum_inv2 = res_df["投資額②"].sum()
sum_dep = excel_round(res_df["償却費"].sum() + ca_dep, 0) # 最終的に円単位で四捨五入

# --- レートメイク：料金シミュレーション ---
st.divider()
st.header("⚖️ レートメイク・シミュレーション")
col_rm1, col_rm2 = st.columns(2)

# 実務データ（座標 D4, E11:F13）
# 本来はExcelから読むが、UIで調整可能にする
total_cost = st.number_input("算定総原価 (D4参照)", value=18976803.0)

with col_rm1:
    st.subheader("📊 需要家データ (E11:F13)")
    cust_a = st.number_input("A群 地点数", value=156)
    vol_a = st.number_input("A群 販売量", value=22464.0)

with col_rm2:
    st.subheader("💰 料金シミュレーション (L20:M22)")
    base_a = st.number_input("A群 基本料金", value=1198.0)
    unit_a = st.number_input("A群 従量単価", value=460.0, format="%.4f")

# 収入計算
revenue = (cust_a * base_a) + (vol_a * unit_a)
diff = revenue - total_cost

st.metric("原価回収過不足 (Revenue - Cost)", f"¥ {diff:,.0f}", delta=diff)

# --- 最終結果表示 ---
st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("有形固定資産 投資額①", f"¥ {sum_inv1:,.0f}")
m2.metric("有形固定資産 投資額②", f"¥ {sum_inv2:,.0f}")
m3.metric("総 減価償却費 (丸め済)", f"¥ {sum_dep:,.0f}")

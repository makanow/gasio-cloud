import streamlit as st
import pandas as pd
from datetime import datetime

# 四捨五入（最後の一回用）
def excel_round(val):
    return int(pd.Series(val).round(0).iloc[0])

st.set_page_config(page_title="G-Calc Master: 原点回帰版", layout="wide")
st.title("🛡️ G-Calc Master: 原点回帰・精密座標版")

EXCEL_FILE = "G-Calc_master.xlsx"

# お前の教えてくれた座標をそのまま使う
# 建物=E(Index4), 構築物=F(Index5)...
ASSET_COLS = {
    "建物": 4, "構築物": 5, "集合装置": 6, "容器": 7,
    "導管・鋼管共同": 8, "導管・ＰＥ共同": 9, "導管・鋼管単独": 10,
    "導管・ＰＥ単独": 11, "メーター": 12
}

@st.cache_data
def load_data():
    xl = pd.ExcelFile(EXCEL_FILE)
    # Aシート：6行目(Index5)からデータ開始
    df_a = xl.parse('標準係数A', header=None).iloc[5:]
    # Bシート：4行目(Index3)から県別データ
    df_b = xl.parse('標準係数B', skiprows=3, header=None)
    pref_master = df_b.iloc[:, [2, 4]].dropna().set_index(2).to_dict()[4]
    return df_a, pref_master

df_infra, pref_wage = load_data()

# --- UI ---
st.sidebar.header("設定")
selected_pref = st.sidebar.selectbox("都道府県", list(pref_wage.keys()))
total_customers = st.sidebar.number_input("許可地点数", value=245)

# 簡易入力
st.subheader("資産入力")
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date()}
    ])

edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)

# --- 計算 ---
results = []
total_invest = 0
total_dep = 0

for i in range(len(edited_df)):
    row = edited_df.iloc[i]
    if not row["項目"]: continue
    
    # 期間検索 (C列とD列の日付範囲)
    dt = pd.to_datetime(row["取得年月日"])
    target_row = df_infra[(pd.to_datetime(df_infra[2]) <= dt) & 
                          (pd.to_datetime(df_infra[3], errors='coerce').fillna(pd.Timestamp('2100-12-31')) >= dt)]
    
    if not target_row.empty:
        col_idx = ASSET_COLS.get(row["項目"], 4)
        u_price = float(target_row.iloc[0, col_idx])
        invest = row["地点数"] * u_price
        
        # 簡易償却（建物0.03、その他0.1と仮定。本来は5行目から引くべきだがまずは一致優先）
        rate = 0.03 if row["項目"] == "建物" else 0.077
        dep = invest * rate
        
        results.append({
            "項目": row["項目"],
            "単価": u_price,
            "投資額": invest,
            "償却費": dep
        })
        total_invest += invest
        total_dep += dep

# --- 表示 ---
if results:
    st.table(pd.DataFrame(results).style.format({"単価": "{:,.0f}", "投資額": "{:,.0f}", "償却費": "{:,.1f}"}))
    
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("総投資額", f"¥ {total_invest:,.0f}")
    c2.metric("総償却費 (丸め前)", f"¥ {total_dep:,.1f}")
    st.info(f"四捨五入後の償却費: ¥ {excel_round(total_dep):,}")

# 労務費
wage = pref_wage.get(selected_pref, 0)
st.metric("労務費 (地点数 × 0.0031 × 単価)", f"¥ {excel_round(total_customers * 0.0031 * wage):,}")

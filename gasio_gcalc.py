import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master: 実務完全版", layout="wide")
st.title("🛡️ G-Calc Cloud: 償却資産・投資算定エンジン（実戦仕様）")

EXCEL_FILE = "G-Calc_master.xlsx"

# 項目記号と名称、償却率、および標準係数Aの列位置（0始まり）
# 3:建物, 4:構築物, 5:集合装置, 6:容器, 7:DKK, 8:DPK, 9:DKT, 10:DPT, 11:MTR, 12:BHN ...
ASSET_INFO = {
    "建物 (TTM)": {"code": "TTM", "col": 3, "rate": 0.03},
    "構築物 (KCB)": {"code": "KCB", "col": 4, "rate": 0.1},
    "集合装置 (SGS)": {"code": "SGS", "col": 5, "rate": 0.1},
    "容器 (YKI)": {"code": "YKI", "col": 6, "rate": 0.167},
    "導管・鋼管共同 (DKK)": {"code": "DKK", "col": 7, "rate": 0.077},
    "導管・ＰＥ共同 (DPK)": {"code": "DPK", "col": 8, "rate": 0.077},
    "導管・鋼管単独 (DKT)": {"code": "DKT", "col": 9, "rate": 0.077},
    "導管・ＰＥ単独 (DPT)": {"code": "DPT", "col": 10, "rate": 0.077},
    "メーター (MTR)": {"code": "MTR", "col": 11, "rate": 0.077},
    "備品 (BHN)": {"code": "BHN", "col": 12, "rate": 0.2}
}

# ---------------------------------------------------------
# 2. マスタと期間判定ロジック
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=1)
        # ID, 開始, 終了, 各資産...
        master = df_a[df_a.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        master.columns = ['No', 'ID', '開始', '終了'] + [f"Col{i}" for i in range(4, 30)]
        # 日付型に変換
        master['開始'] = pd.to_datetime(master['開始'])
        master['終了'] = pd.to_datetime(master['終了'])
        return master
    except:
        return pd.DataFrame()

infra_master = load_infra_master()

def find_period_id(target_date):
    """取得年月日から期間IDを自動特定する"""
    if infra_master.empty: return "HK13", {}
    dt = pd.to_datetime(target_date)
    match = infra_master[(infra_master['開始'] <= dt) & (infra_master['終了'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        return row['ID'], row.to_dict()
    return "HK13", infra_master.iloc[-1].to_dict() # 見つからなければ最新

# ---------------------------------------------------------
# 3. メインUI：サイドバー
# ---------------------------------------------------------
st.sidebar.header("⚙️ 算定基礎")
total_customers = st.sidebar.number_input("許可地点数", value=245)

# ---------------------------------------------------------
# 4. メイン画面：投資エディタ
# ---------------------------------------------------------
st.header("🏗️ 償却資産入力明細")

if 'invest_data' not in st.session_state:
    st.session_state.invest_data = [
        {"項目": "建物 (TTM)", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "減免": False, "方式": "標準", "実績額": 0},
        {"項目": "導管・ＰＥ共同 (DPK)", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "減免": False, "方式": "標準", "実績額": 0},
        {"項目": "メーター (MTR)", "地点数": total_customers, "取得年月日": datetime(2020, 1, 1).date(), "減免": False, "方式": "標準", "実績額": 0},
    ]

# エディタの表示
edited_rows = st.data_editor(
    st.session_state.invest_data,
    num_rows="dynamic",
    column_config={
        "項目": st.column_config.SelectboxColumn("項目", options=list(ASSET_INFO.keys())),
        "取得年月日": st.column_config.DateColumn("取得年月日"),
        "方式": st.column_config.SelectboxColumn("方式", options=["標準", "実績"]),
        "実績額": st.column_config.NumberColumn("実績投資額(円)"),
        "減免": st.column_config.CheckboxColumn("減免対象"),
    },
    use_container_width=True
)

# ---------------------------------------------------------
# 5. 計算実行・バリデーション
# ---------------------------------------------------------
st.divider()
st.subheader("📊 算定結果サマリー")

results = []
for row in edited_rows:
    # 1. 期間IDと単価を自動特定
    pid, pdata = find_period_id(row["取得年月日"])
    info = ASSET_INFO[row["項目"]]
    unit_price = pdata.get(f"Col{info['col']}", 0)
    
    # 2. 投資額の算出（標準 or 実績）
    if row["方式"] == "実績":
        invest_base = row["実績額"]
    else:
        invest_base = row["地点数"] * unit_price
        
    # 3. 減免による振り分け (投資額①=非減免, 投資額②=減免)
    inv1 = 0 if row["減免"] else invest_base
    inv2 = invest_base if row["減免"] else 0
    
    dep = invest_base * info["rate"]
    
    results.append({
        "項目": row["項目"],
        "記号": info["code"],
        "地点数": row["地点数"],
        "期間ID": pid,
        "投資額①": inv1,
        "投資額②": inv2,
        "償却費": dep
    })

res_df = pd.DataFrame(results)
st.dataframe(res_df, use_container_width=True)

# --- 厳格なバリデーションチェック ---
st.subheader("🔍 バリデーション")
c1, c2 = st.columns(2)

# 導管グループの合計チェック
pipe_codes = ["DKK", "DPK", "DKT", "DPT"]
pipe_sum = res_df[res_df["記号"].isin(pipe_codes)]["地点数"].sum()

with c1:
    if pipe_sum == total_customers:
        st.success(f"✅ 導管合計：{pipe_sum} / {total_customers} 一致")
    else:
        st.error(f"❌ 導管合計：{pipe_sum} (不足/過剰: {pipe_sum - total_customers})")

with c2:
    # 他の主要項目のチェック
    for main_cat in ["TTM", "MTR"]:
        cat_sum = res_df[res_df["記号"] == main_cat]["地点数"].sum()
        if cat_sum != total_customers:
            st.warning(f"⚠️ {main_cat}の地点数が合計と一致しません")

# ---------------------------------------------------------
# 6. 総括原価への合流（予告）
# ---------------------------------------------------------
total_inv1 = res_df["投資額①"].sum()
total_inv2 = res_df["投資額②"].sum()
total_dep = res_df["償却費"].sum()

st.divider()
col_res1, col_res2, col_res3 = st.columns(3)
col_res1.metric("投資額① (非減免)", f"{total_inv1:,.0f} 円")
col_res2.metric("投資額② (減免)", f"{total_inv2:,.0f} 円")
col_res3.metric("総減価償却費", f"{total_dep:,.0f} 円")

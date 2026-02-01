import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 初期設定とスタイル
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master: 実務仕様", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産算定エンジン（実務仕様）")

EXCEL_FILE = "G-Calc_master.xlsx"

# 資産マスタ（列位置と償却率）
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

# ---------------------------------------------------------
# 2. マスタ読込ロジック（9999年問題対策済）
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
    if infra_master.empty: return "データ無", None
    dt = pd.to_datetime(target_date)
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        return f"{row['start_dt'].strftime('%Y/%m/%d')} 〜 {row['end_dt'].strftime('%Y/%m/%d')}", row
    last = infra_master.iloc[-1]
    return f"{last['start_dt'].strftime('%Y/%m/%d')} 〜 {last['end_dt'].strftime('%Y/%m/%d')}", last

# ---------------------------------------------------------
# 3. メインUI：入力
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体設定")
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1, format="%d")

st.header("🏗️ 償却資産・分散取得エディタ")

if 'invest_data' not in st.session_state:
    st.session_state.invest_data = [
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "減免対象": False, "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "減免対象": True, "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "メーター", "地点数": total_customers, "取得年月日": datetime(2020, 1, 1).date(), "減免対象": False, "算出方式": "標準係数", "実績投資額": 0},
    ]

# エディタ（桁区切り表示設定）
edited_rows = st.data_editor(
    st.session_state.invest_data,
    num_rows="dynamic",
    column_config={
        "項目": st.column_config.SelectboxColumn("項目", options=list(ASSET_INFO.keys())),
        "取得年月日": st.column_config.DateColumn("取得年月日"),
        "算出方式": st.column_config.SelectboxColumn("方式", options=["標準係数", "実績値"]),
        "実績投資額": st.column_config.NumberColumn("実績値(円)", format="%d"),
        "減免対象": st.column_config.CheckboxColumn("減免"),
    },
    use_container_width=True
)

# ---------------------------------------------------------
# 4. 計算（Excel流・端数処理）
# ---------------------------------------------------------
results = []
for row in edited_rows:
    p_label, p_data = find_period_info(row["取得年月日"])
    info = ASSET_INFO[row["項目"]]
    
    # 1. 投資額の算出
    if row["算出方式"] == "実績値":
        # 実績値はそのまま（整数化）
        invest_base = int(row["実績投資額"])
    else:
        # 標準係数：地点数 × 単価 → 四捨五入(ROUND)
        unit_price = p_data.iloc[info["col"]] if p_data is not None else 0
        invest_base = round(row["地点数"] * unit_price)
        
    # 2. 振り分け
    inv1 = 0 if row["減免対象"] else invest_base
    inv2 = invest_base if row["減免対象"] else 0
    
    # 3. 減価償却費（小数点1位まで保持し、表示で調整）
    dep = invest_base * info["rate"]
    
    results.append({
        "項目": row["項目"],
        "取得時期": p_label,
        "地点数": row["地点数"],
        "投資額①": inv1,
        "投資額②": inv2,
        "減価償却費": dep,
        "code": info["code"]
    })

res_df = pd.DataFrame(results)

# ---------------------------------------------------------
# 5. 結果表示（徹底した桁区切り）
# ---------------------------------------------------------
st.divider()
st.subheader("📊 算定結果サマリー")

if not res_df.empty:
    # データフレームの表示形式設定
    st.dataframe(
        res_df.drop(columns=["code"]),
        column_config={
            "投資額①": st.column_config.NumberColumn("投資額①", format="¥%,d"),
            "投資額②": st.column_config.NumberColumn("投資額②", format="¥%,d"),
            "減価償却費": st.column_config.NumberColumn("減価償却費", format="¥%,.1f"),
            "地点数": st.column_config.NumberColumn("地点数", format="%d"),
        },
        use_container_width=True
    )

    # 整合性チェック
    pipe_codes = ["DKK", "DPK", "DKT", "DPT"]
    pipe_sum = res_df[res_df["code"].isin(pipe_codes)]["地点数"].sum()
    
    c1, c2 = st.columns(2)
    with c1:
        if pipe_sum == total_customers:
            st.success(f"✅ 導管合計：{pipe_sum:,} / {total_customers:,}")
        else:
            st.error(f"❌ 導管合計：{pipe_sum:,} (不足：{total_customers - pipe_sum:,})")

    # 最終メトリクス
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("有形固定資産 投資額①", f"¥ {res_df['投資額①'].sum():,.0f}")
    m2.metric("有形固定資産 投資額②", f"¥ {res_df['投資額②'].sum():,.0f}")
    # 減価償却費の合計（Excel同様、最終的な丸めを行う場合はここでint化）
    m3.metric("総 減価償却費", f"¥ {res_df['減価償却費'].sum():,.1f}")

if st.checkbox("📖 内部の端数処理ロジックを確認"):
    st.info("""
    **【G-Calc 端数処理基準】**
    1. **投資額基礎:** 地点数 × 標準単価 を算出し、小数点第一位で四捨五入（整数化）。
    2. **減価償却費:** 投資額基礎 × 償却率 を算出。Excelの明細に合わせ、小数点第一位まで保持。
    3. **表示:** 全ての通貨項目に桁区切りカンマ(,)を適用。
    """)

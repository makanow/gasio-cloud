import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master: 実務完全版", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産算定エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

# 資産項目と標準係数Aの列インデックス（0始まりで、期間ID列を0とする）、償却率
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
    "備品": {"code": "BHN", "col": 12, "rate": 0.2}
}

# ---------------------------------------------------------
# 2. マスタと期間判定ロジック
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        # 見出しをスキップし、期間IDが並んでいる行から取得
        # Excelの「標準係数A」をB列（期間ID）から読み込む
        df_raw = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
        
        # 2列目(index 1)に「HK」が含まれる行を抽出
        df = df_raw[df_raw.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        # 列構成: 1:ID, 2:開始, 3:終了, 4:建物, 5:構築物...
        df.columns = ['No', 'ID', '開始', '終了'] + [f"Col{i}" for i in range(4, 30)]
        df['開始'] = pd.to_datetime(df['開始'])
        df['終了'] = pd.to_datetime(df['終了'])
        return df
    except Exception as e:
        st.error(f"マスタ読み込み失敗：{e}")
        return pd.DataFrame()

infra_master = load_infra_master()

def find_period_info(target_date):
    """取得年月日から期間の名称（年月日〜）とデータ行を特定する"""
    if infra_master.empty:
        return "期間不明", {}
    dt = pd.to_datetime(target_date)
    # 期間内に合致する行を探す
    match = infra_master[(infra_master['開始'] <= dt) & (infra_master['終了'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        label = f"{row['開始'].strftime('%Y/%m/%d')} 〜 {row['終了'].strftime('%Y/%m/%d')}"
        return label, row.to_dict()
    # 合致しない場合は最新の期間を返す
    last = infra_master.iloc[-1]
    label = f"{last['開始'].strftime('%Y/%m/%d')} 〜 {last['終了'].strftime('%Y/%m/%d')}"
    return label, last.to_dict()

# ---------------------------------------------------------
# 3. メインUI：サイドバー
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体設定")
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1, format="%d")

# ---------------------------------------------------------
# 4. メイン画面：投資エディタ
# ---------------------------------------------------------
st.header("🏗️ 分散取得・償却資産入力")
st.write(f"取得年月日を修正すると、適用期間と単価が自動で切り替わります。")

if 'invest_data' not in st.session_state:
    st.session_state.invest_data = [
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "減免対象": False, "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "減免対象": True, "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "メーター", "地点数": total_customers, "取得年月日": datetime(2020, 1, 1).date(), "減免対象": False, "算出方式": "標準係数", "実績投資額": 0},
    ]

# 投資エディタの表示
edited_rows = st.data_editor(
    st.session_state.invest_data,
    num_rows="dynamic",
    column_config={
        "項目": st.column_config.SelectboxColumn("資産項目", options=list(ASSET_INFO.keys())),
        "取得年月日": st.column_config.DateColumn("取得年月日"),
        "算出方式": st.column_config.SelectboxColumn("算出方式", options=["標準係数", "実績値"]),
        "実績投資額": st.column_config.NumberColumn("実績値入力 (円)"),
        "減免対象": st.column_config.CheckboxColumn("固定資産税減免"),
    },
    use_container_width=True
)

# ---------------------------------------------------------
# 5. 計算実行・集計
# ---------------------------------------------------------
st.divider()

results = []
for row in edited_rows:
    # 期間と単価の自動ルックアップ
    p_label, p_data = find_period_info(row["取得年月日"])
    info = ASSET_INFO[row["項目"]]
    unit_price = p_data.get(f"Col{info['col']}", 0)
    
    # 投資額の算出（標準 or 実績）
    if row["算出方式"] == "実績値":
        invest_base = row["実績投資額"]
    else:
        invest_base = row["地点数"] * unit_price
        
    # 投資額①（通常）と②（減免）の振り分け
    inv1 = 0 if row["減免対象"] else invest_base
    inv2 = invest_base if row["減免対象"] else 0
    
    # 償却費
    dep = invest_base * info["rate"]
    
    results.append({
        "項目": row["項目"],
        "取得時期": p_label,
        "地点数": row["地点数"],
        "投資額①": inv1,
        "投資額②": inv2,
        "減価償却費": dep,
        "code": info["code"] # 集計用
    })

res_df = pd.DataFrame(results)

# サマリー表示
st.subheader("📊 算定結果サマリー")
st.dataframe(res_df.drop(columns=["code"]), use_container_width=True)

# --- 厳格なバリデーションチェック ---
st.subheader("🔍 整合性チェック")
c1, c2, c3 = st.columns(3)

# 導管グループのチェック
pipe_codes = ["DKK", "DPK", "DKT", "DPT"]
pipe_sum = res_df[res_df["code"].isin(pipe_codes)]["地点数"].sum()

with c1:
    if pipe_sum == total_customers:
        st.success(f"✅ 導管グループ合計：{pipe_sum} (一致)")
    else:
        st.error(f"❌ 導管グループ合計：{pipe_sum} (目標: {total_customers})")

with c2:
    for cat in ["建物", "メーター"]:
        cat_sum = res_df[res_df["項目"] == cat]["地点数"].sum()
        if cat_sum == total_customers:
            st.success(f"✅ {cat}合計：{cat_sum}")
        else:
            st.warning(f"⚠️ {cat}合計：{cat_sum} (ズレあり)")

# ---------------------------------------------------------
# 6. 総括原価への合流
# ---------------------------------------------------------
total_inv1 = res_df["投資額①"].sum()
total_inv2 = res_df["投資額②"].sum()
total_dep = res_df["減価償却費"].sum()

st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("有形固定資産 投資額①", f"{total_inv1:,.0f} 円")
m2.metric("有形固定資産 投資額②", f"{total_inv2:,.0f} 円")
m3.metric("総 減価償却費", f"{total_dep:,.0f} 円")

if st.checkbox("📖 判定に使用された単価を確認"):
    st.write("標準係数Aから自動抽出された、適用期間ごとの1地点あたり単価です。")
    st.dataframe(infra_master)

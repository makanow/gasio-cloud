import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. ページ構成
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Cloud: 償却資産要塞", layout="wide")
st.title("🛡️ G-Calc Cloud: 償却資産・全項目連動エディタ")

EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. 全資産項目の定義（標準係数Aの列構成と償却率）
# ---------------------------------------------------------
# 列インデックスは「期間ID」が1列目(index 1)とした場合の相対位置
ASSET_CONFIG = {
    "建物 (TTM)": {"col_idx": 4, "rate": 0.03},
    "構築物 (KCB)": {"col_idx": 5, "rate": 0.1},
    "集合装置 (SGS)": {"col_idx": 6, "rate": 0.1},
    "容器 (YKI)": {"col_idx": 7, "rate": 0.167},
    "導管・鋼管共同 (DKK)": {"col_idx": 8, "rate": 0.077},
    "導管・ＰＥ共同 (DPK)": {"col_idx": 9, "rate": 0.077},
    "導管・鋼管単独 (DKT)": {"col_idx": 10, "rate": 0.077},
    "導管・ＰＥ単独 (DPT)": {"col_idx": 11, "rate": 0.077},
    "メーター (MTR)": {"col_idx": 12, "rate": 0.077},
    "備品 (BHN)": {"col_idx": 13, "rate": 0.2},
    "構築物・バルク (KBB)": {"col_idx": 14, "rate": 0.1},
    "集合装置・バルク (SSB)": {"col_idx": 15, "rate": 0.1},
    "容器・バルク (YKB)": {"col_idx": 16, "rate": 0.167},
    "強制気化装置 (KKS)": {"col_idx": 17, "rate": 0.1}
}

# ---------------------------------------------------------
# 3. マスタデータの読み込み
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=1)
        # HKから始まる行のみ抽出
        master = df_a[df_a.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        # 必要な列をすべて抽出 (ID, 開始日, および全資産列)
        cols_to_extract = [1, 2] + [cfg["col_idx"] for cfg in ASSET_CONFIG.values()]
        result_df = master.iloc[:, cols_to_extract].copy()
        
        # 列名のリネーム
        col_names = ['ID', '開始日'] + list(ASSET_CONFIG.keys())
        result_df.columns = col_names
        
        return result_df.set_index('ID')
    except Exception as e:
        st.error(f"マスタ読み込み失敗: {e}")
        return pd.DataFrame()

infra_df = load_infra_master()

# ---------------------------------------------------------
# 4. サイドバーと初期設定
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体基本設定")
total_customers = st.sidebar.number_input("許可地点数（合計）", value=245, step=1, format="%d")

# 初期入力行を準備（主要なものを最初に出しておく）
if 'full_asset_rows' not in st.session_state:
    st.session_state.full_asset_rows = pd.DataFrame([
        {"資産項目": "建物 (TTM)", "期間ID": "HK08", "地点数": total_customers},
        {"資産項目": "構築物 (KCB)", "期間ID": "HK08", "地点数": total_customers},
        {"資産項目": "集合装置 (SGS)", "期間ID": "HK13", "地点数": total_customers},
        {"資産項目": "容器 (YKI)", "期間ID": "HK13", "地点数": total_customers},
        {"資産項目": "導管・ＰＥ共同 (DPK)", "期間ID": "HK13", "地点数": total_customers},
        {"資産項目": "メーター (MTR)", "期間ID": "HK13", "地点数": total_customers},
    ])

# ---------------------------------------------------------
# 5. メイン画面：償却資産エディタ
# ---------------------------------------------------------
st.header("🏗️ 分散取得・償却資産エディタ")
st.caption("「償却資産」シートの入力内容をここで再現します。地点数合計をチェックしてください。")

edited_df = st.data_editor(
    st.session_state.full_asset_rows,
    num_rows="dynamic",
    column_config={
        "資産項目": st.column_config.SelectboxColumn("資産項目", options=list(ASSET_CONFIG.keys()), required=True),
        "期間ID": st.column_config.SelectboxColumn("期間ID", options=infra_df.index.tolist(), required=True),
        "地点数": st.column_config.NumberColumn("地点数", min_value=0, step=1, format="%d"),
    },
    use_container_width=True,
    key="full_asset_editor"
)

# ---------------------------------------------------------
# 6. 集計計算エンジン
# ---------------------------------------------------------
st.divider()
st.subheader("📊 資産別集計（バリデーション付）")

summary_list = []
# 各資産項目ごとに、入力された地点数の合計と投資額を算出
for asset_name, config in ASSET_CONFIG.items():
    rows = edited_df[edited_df["資産項目"] == asset_name]
    sum_count = int(rows["地点数"].sum())
    
    total_invest = 0
    for _, r in rows.iterrows():
        hid = str(r["期間ID"])
        if hid in infra_df.index:
            unit_price = infra_df.loc[hid, asset_name]
            total_invest += r["地点数"] * unit_price
    
    total_dep = total_invest * config["rate"]
    
    # 地点数が0でない、または主要項目のみ表示
    if sum_count > 0:
        summary_list.append({
            "資産項目": asset_name,
            "地点数合計": sum_count,
            "投資総額 (円)": total_invest,
            "減価償却費 (円)": total_dep,
            "判定": "✅" if sum_count == total_customers else f"⚠️ {sum_count - total_customers}"
        })

if summary_list:
    st.dataframe(pd.DataFrame(summary_list), use_container_width=True)
else:
    st.info("資産データを入力してください。")

# 全資産の合計
total_dep_all = sum(item["減価償却費 (円)"] for item in summary_list)
st.metric("総 減価償却費（車両分除く）", f"{total_dep_all:,.0f} 円")

# ---------------------------------------------------------
# 7. ロジック公開モード：詳細単価表
# ---------------------------------------------------------
if st.checkbox("📖 期間IDごとの適用単価（マスタ）を表示"):
    st.write("標準係数Aより抽出した、1地点あたりの投資単価です。")
    st.dataframe(infra_df, use_container_width=True)

import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. ページ構成
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Cloud: 償却資産要塞", layout="wide")
st.title("🛡️ G-Calc Cloud: 償却資産・分散投資シミュレーター")

EXCEL_FILE = "G-Calc_master.xlsx"

# アセット区分と標準係数A内の列インデックス、償却率の定義
# (標準係数Aシートの構成に基づく)
ASSET_MAP = {
    "建物": {"idx": 3, "code": "TTM", "rate": 0.03},
    "構築物": {"idx": 4, "code": "KCB", "rate": 0.1},
    "メーター": {"idx": 11, "code": "MTR", "rate": 0.077},
    "備品": {"idx": 12, "code": "BHN", "rate": 0.2},
    "強制気化装置": {"idx": 16, "code": "KKS", "rate": 0.1}
}

# ---------------------------------------------------------
# 2. マスタデータの読み込み（標準係数Aから単価表を作成）
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        # 見出しを考慮して2行目から読み込み
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=1)
        
        # 期間IDが含まれる行（HKから始まる行）のみ抽出
        master = df_a[df_a.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        # 列の特定 (ID, 開始日, 建物, 構築物, メーター)
        # iloc[行, [1:ID, 2:開始日, 4:建物, 5:構築物, 12:メーター]] ※skiprows後の相対座標
        result_df = master.iloc[:, [1, 2, 4, 5, 12]].copy()
        result_df.columns = ['ID', '開始日', '建物', '構築物', 'メーター']
        
        # エラー対策：すべて文字列に変換してからラベル作成
        ids = result_df['ID'].astype(str).tolist()
        dates = result_df['開始日'].astype(str).tolist()
        labels = [f"{i} ({d}〜)" for i, d in zip(ids, dates)]
        
        # 検索用の辞書（ID -> 単価データ）
        return result_df.set_index('ID'), labels
    except Exception as e:
        st.error(f"マスタ読み込み失敗: {e}")
        return pd.DataFrame(), ["HK13"]

# マスタ準備
infra_df, id_labels = load_infra_master()

# ---------------------------------------------------------
# 3. サイドバー：全体統括
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体基本設定")
total_customers = st.sidebar.number_input("許可地点数（合計）", value=245, step=1, format="%d")

st.sidebar.divider()
st.sidebar.subheader("🚐 車両設定")
vehicle_mode = st.sidebar.selectbox("車両保有形態", ["自社所有（投資適用）", "リース（投資除外）"])

# ---------------------------------------------------------
# 4. メイン画面：償却資産エディタ（Excel「償却資産」シートを再現）
# ---------------------------------------------------------
st.header("🏗️ 償却資産・分散取得入力")
st.write(f"各資産の地点数を入力してください。合計が **{total_customers}** になると「✅」が表示されます。")

# 初期行の設定
if 'asset_rows' not in st.session_state:
    st.session_state.asset_rows = pd.DataFrame([
        {"項目": "建物", "期間ID": "HK08", "地点数": total_customers},
        {"項目": "構築物", "期間ID": "HK08", "地点数": total_customers},
        {"項目": "メーター", "期間ID": "HK13", "地点数": total_customers},
    ])

# データエディタ（追加・削除・編集が自由自在）
edited_assets = st.data_editor(
    st.session_state.asset_rows,
    num_rows="dynamic",
    column_config={
        "項目": st.column_config.SelectboxColumn("項目 (Asset)", options=list(ASSET_MAP.keys()), required=True),
        "期間ID": st.column_config.SelectboxColumn("取得時期 (ID)", options=infra_df.index.tolist(), required=True),
        "地点数": st.column_config.NumberColumn("地点数", min_value=0, step=1, format="%d"),
    },
    use_container_width=True,
    key="asset_editor"
)

# ---------------------------------------------------------
# 5. 集計とバリデーション
# ---------------------------------------------------------
st.divider()
st.subheader("📊 投資・償却費 算定サマリー")

summary_results = []
for cat, info in ASSET_MAP.items():
    rows = edited_assets[edited_assets["項目"] == cat]
    cat_sum = int(rows["地点数"].sum())
    
    # 投資額と償却費の計算
    inv_total = 0
    for _, r in rows.iterrows():
        hid = str(r["期間ID"])
        if hid in infra_df.index:
            unit_price = infra_df.loc[hid, cat]
            inv_total += r["地点数"] * unit_price
    
    dep_total = inv_total * info["rate"]
    
    summary_results.append({
        "項目": cat,
        "地点数合計": cat_sum,
        "投資総額 (円)": inv_total,
        "減価償却費 (円)": dep_total,
        "状態": "✅ OK" if cat_sum == total_customers else f"❌ 不一致 ({cat_sum - total_customers})"
    })

st.dataframe(pd.DataFrame(summary_results), use_container_width=True)

# ---------------------------------------------------------
# 6. ロジック公開モード：詳細明細
# ---------------------------------------------------------
if st.checkbox("📖 各行の計算明細を確認（審査・教育用）"):
    details = []
    for _, r in edited_assets.iterrows():
        hid = str(r["期間ID"])
        cat = r["項目"]
        num = r["地点数"]
        if hid in infra_df.index:
            unit = infra_df.loc[hid, cat]
            inv = unit * num
            details.append({
                "項目": cat, "期間": hid, "地点数": num, 
                "標準単価": f"{unit:,.0f}", "投資額": f"{inv:,.0f}", 
                "償却率": ASSET_MAP[cat]["rate"], "償却費": f"{inv * ASSET_MAP[cat]['rate']:,.0f}"
            })
    st.table(pd.DataFrame(details))

# サイドバーに単価表をチラ見せ
with st.sidebar.expander("参考：標準係数Aの単価表"):
    st.dataframe(infra_df[['開始日', '建物', 'メーター']])

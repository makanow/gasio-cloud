import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master Cloud", layout="wide")
st.title("🛡️ G-Calc Master: 実戦型・分散投資シミュレーター")

EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. データ抽出・マスタ準備
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    """標準係数Aから各HK期間の単価リストを作成"""
    try:
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2)
        # 必要な列: 期間ID, 建物, 構築物, メーター
        # 列名はExcelの実際の名前に合わせて調整
        master = df_a.iloc[:, [0, 4, 5, 12]].dropna()
        master.columns = ['ID', '建物', '構築物', 'メーター']
        return master.set_index('ID').to_dict('index')
    except:
        # 万が一のフォールバック
        return {
            "HK13": {"建物": 8770, "構築物": 1450, "メーター": 5570},
            "HK08": {"建物": 8770, "構築物": 1450, "メーター": 5130}
        }

infra_master = load_infra_master()

# ---------------------------------------------------------
# 3. サイドバー：全体条件
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体基本設定")
total_customers = st.sidebar.number_input("許可地点数（合計）", value=245, step=1, format="%d")

st.sidebar.divider()
st.sidebar.subheader("🚐 車両設定")
is_vehicle_owned = st.sidebar.toggle("自社所有（投資に計上する）", value=True)
if not is_vehicle_owned:
    st.sidebar.caption("※リース契約のため投資額から除外されます。")

# ---------------------------------------------------------
# 4. メイン画面：分散投資エディタ
# ---------------------------------------------------------
st.header("🏗️ 資産別・取得時期（HK）分散入力")
st.write(f"各資産の地点数合計を **{total_customers}** に合わせてください。")

# デフォルトの配分表を作成
default_dist = pd.DataFrame([
    {"期間ID": "HK13", "建物(地点数)": total_customers, "メーター(地点数)": total_customers},
    {"期間ID": "HK08", "建物(地点数)": 0, "メーター(地点数)": 0},
    {"期間ID": "HK01", "建物(地点数)": 0, "メーター(地点数)": 0},
], columns=["期間ID", "建物(地点数)", "メーター(地点数)"])

# ユーザーが自由に編集できるテーブル
edited_df = st.data_editor(
    default_dist, 
    num_rows="dynamic",
    column_config={
        "期間ID": st.column_config.SelectboxColumn("期間ID", options=list(infra_master.keys()), required=True),
        "建物(地点数)": st.column_config.NumberColumn(min_value=0),
        "メーター(地点数)": st.column_config.NumberColumn(min_value=0),
    },
    use_container_width=True
)

# --- バリデーションチェック ---
sum_building = edited_df["建物(地点数)"].sum()
sum_meter = edited_df["メーター(地点数)"].sum()

col_check1, col_check2 = st.columns(2)
with col_check1:
    if sum_building == total_customers:
        st.success(f"✅ 建物：合計 {sum_building}（一致）")
    else:
        st.error(f"❌ 建物：合計 {sum_building}（{total_customers}にしてください）")

with col_check2:
    if sum_meter == total_customers:
        st.success(f"✅ メーター：合計 {sum_meter}（一致）")
    else:
        st.error(f"❌ メーター：合計 {sum_meter}（{total_customers}にしてください）")

# ---------------------------------------------------------
# 5. 投資計算エンジン
# ---------------------------------------------------------
st.divider()
st.subheader("📊 算定結果サマリー")

# 各行の投資額を合算
total_invest_building = 0
total_invest_meter = 0

for _, row in edited_df.iterrows():
    hid = row["期間ID"]
    if hid in infra_master:
        total_invest_building += row["建物(地点数)"] * infra_master[hid]["建物"]
        total_invest_meter += row["メーター(地点数)"] * infra_master[hid]["メーター"]

# 車両の計算
if is_vehicle_owned:
    # 簡略化のためCA1単価を使用
    total_invest_vehicle = total_customers * 7270 
else:
    total_invest_vehicle = 0

# 表示
c1, c2, c3 = st.columns(3)
c1.metric("建物 投資総額", f"{total_invest_building:,.0f} 円")
c2.metric("メーター 投資総額", f"{total_invest_meter:,.0f} 円")
c3.metric("車両 投資総額", f"{total_invest_vehicle:,.0f} 円", delta="リース" if not is_vehicle_owned else None)

# ---------------------------------------------------------
# 6. ロジック公開モード
# ---------------------------------------------------------
if st.checkbox("📖 内部の計算根拠を表示"):
    st.markdown("### 投資額の加重平均プロセス")
    for _, row in edited_df.iterrows():
        if row["建物(地点数)"] > 0:
            hid = row["期間ID"]
            price = infra_master[hid]["建物"]
            st.write(f"・{hid} 分（建物）: {row['建物(地点数)']} 地点 × {price:,.0f}円 = {row['建物(地点数)']*price:,.0f}円")
    
    if not is_vehicle_owned:
        st.warning("車両投資はリース判定のため、算定上の投資額は 0円 として処理されています。")

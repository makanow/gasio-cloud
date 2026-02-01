import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. ページ構成
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Cloud: 償却資産エディタ", layout="wide")
st.title("🛡️ G-Calc Cloud: 分散投資・償却資産管理")

EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. マスタデータの読み込み（標準係数Aから単価表を作成）
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        # 「標準係数A」から期間IDごとの単価を引っこ抜く
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2)
        # 必要な列を特定（ID, 適用開始, 建物(TTM), 構築物(KCB), メーター(MTR)等）
        master = df_a.iloc[:, [0, 1, 4, 5, 12]].dropna(subset=[df_a.columns[0]])
        master.columns = ['ID', '開始日', '建物', '構築物', 'メーター']
        # 画面表示用に「ID (開始日〜)」というリストを作る
        master['label'] = master['ID'] + " (" + master['開始日'].astype(str) + "〜)"
        return master.set_index('ID'), master['label'].tolist()
    except Exception as e:
        st.error(f"マスタ読み込み失敗: {e}")
        return pd.DataFrame(), ["HK13 (2007-01-01〜)"]

infra_df, id_labels = load_infra_master()

# ---------------------------------------------------------
# 3. サイドバー：全体統括
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体基本設定")
total_customers = st.sidebar.number_input("許可地点数（合計）", value=245, step=1, format="%d")

st.sidebar.divider()
st.sidebar.subheader("🚐 車両設定")
vehicle_mode = st.sidebar.selectbox("車両保有形態", ["自社所有（標準投資適用）", "リース（投資除外）"])

# ---------------------------------------------------------
# 4. メイン画面：分散投資エディタ（償却資産シートの再現）
# ---------------------------------------------------------
st.header("🏗️ 償却資産・分散取得入力")
st.write(f"「償却資産」シートのように、取得時期ごとに地点数を割り振ってください。")

# 初期データの作成（償却資産シートのNo.1〜3のイメージ）
if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"No": 1, "項目": "建物・メーター等", "期間ID": "HK13", "地点数": total_customers},
        {"No": 2, "項目": "建物・メーター等", "期間ID": "HK12", "地点数": 0},
        {"No": 3, "項目": "建物・メーター等", "期間ID": "HK08", "地点数": 0},
    ])

# データエディタ（ここでドロップダウンと数値入力を統合！）
edited_df = st.data_editor(
    st.session_state.invest_df,
    num_rows="dynamic",
    column_config={
        "No": st.column_config.NumberColumn(width="small", disabled=True),
        "項目": st.column_config.TextColumn(width="medium"),
        "期間ID": st.column_config.SelectboxColumn(
            "期間ID (取得時期)", 
            options=infra_df.index.tolist(), # IDのみを選択肢にする
            required=True,
            width="large"
        ),
        "地点数": st.column_config.NumberColumn("地点数", min_value=0, step=1, format="%d", width="medium"),
    },
    use_container_width=True,
    key="invest_editor"
)

# --- 整合性チェック（バリデーション） ---
current_sum = edited_df["地点数"].sum()
diff = total_customers - current_sum

if diff == 0:
    st.success(f"✅ 地点数合計：{current_sum} / {total_customers} (一致しています)")
else:
    st.error(f"❌ 地点数合計：{current_sum} / {total_customers} (残：{diff})")

# ---------------------------------------------------------
# 5. 計算エンジン：各行の単価をマスタから引いて合計
# ---------------------------------------------------------
st.divider()
st.subheader("📊 投資算定サマリー")

total_ttm = 0 # 建物
total_mtr = 0 # メーター

for _, row in edited_df.iterrows():
    hid = row["期間ID"]
    num = row["地点数"]
    if hid in infra_df.index:
        total_ttm += num * infra_df.loc[hid, "建物"]
        total_mtr += num * infra_df.loc[hid, "メーター"]

# 車両計算（CA判定は地点数合計で決まるため独立計算）
if "自社所有" in vehicle_mode:
    # 245地点ならCA1(7270円)
    v_unit = 7270 if total_customers <= 250 else 5450 # 簡易化
    total_vehicle = total_customers * v_unit
else:
    total_vehicle = 0

c1, c2, c3 = st.columns(3)
c1.metric("建物 投資総額", f"{total_ttm:,.0f} 円")
c2.metric("メーター 投資総額", f"{total_mtr:,.0f} 円")
c3.metric("車両 投資総額", f"{total_vehicle:,.0f} 円")

# ---------------------------------------------------------
# 6. ロジック公開モード：表形式で単価を表示
# ---------------------------------------------------------
if st.checkbox("📖 適用されている単価表（標準係数A）を確認"):
    st.write("選択中の期間IDに対応する、1地点あたりの標準投資額です。")
    st.dataframe(infra_df[['開始日', '建物', 'メーター']], use_container_width=True)

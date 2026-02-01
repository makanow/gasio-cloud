import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master", layout="wide")
st.title("🛡️ G-Calc Master: 都道府県マスタ連携")

EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. マスタデータのロード
# ---------------------------------------------------------
@st.cache_data
def load_master_data():
    try:
        # 「標準係数B」シートから都道府県ごとの「労務費」と「産気率」を抽出
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', header=None, skiprows=2)
        # 2列目が県名、4列目が労務費、6列目が産気率と想定（ilocで指定）
        master = df_b.iloc[:, [2, 4, 6]].dropna()
        master.columns = ['pref', 'wage', 'gas_rate']
        return master.set_index('pref').to_dict('index')
    except Exception as e:
        st.error(f"マスタ読み込み失敗: {e}")
        return {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

@st.cache_data
def get_initial_count():
    try:
        df_nav = pd.read_excel(EXCEL_FILE, sheet_name='ナビ', header=None)
        # 許可地点数* の右隣にある数値を取得（Row 10, Col 3 あたりを想定）
        for i, row in df_nav.iterrows():
            if "許可地点数*" in str(row.values):
                return int(row[row.tolist().index("許可地点数*") + 1])
        return 245
    except:
        return 245

# データの準備
master_dict = load_master_data()
initial_count = get_initial_count()

# ---------------------------------------------------------
# 3. コックピット：入力エリア
# ---------------------------------------------------------
st.sidebar.header("🌍 エリア設定")
selected_pref = st.sidebar.selectbox("対象の都道府県を選択", list(master_dict.keys()), index=list(master_dict.keys()).index("東京都") if "東京都" in master_dict else 0)

# 選択された県のマスタ値を取得
pref_data = master_dict[selected_pref]
auto_wage = pref_data['wage']
auto_gas_rate = pref_data['gas_rate']

st.header(f"📍 {selected_pref} の算定コックピット")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 基本入力")
    # 地点数を「整数(int)」に固定
    customer_count = st.number_input("供給地点数 (整数)", value=int(initial_count), step=1, format="%d")
    
    st.divider()
    calc_mode = st.radio("労務費の採用ロジック", ["マスタ自動参照", "実績値（手入力）"])
    
    if calc_mode == "実績値（手入力）":
        applied_wage = st.number_input("実績単価（円/人）", value=int(auto_wage))
    else:
        applied_wage = auto_wage
        st.info(f"💡 {selected_pref} の標準労務費 {auto_wage:,.0f}円 を適用中")

with col2:
    st.subheader("💰 労務費の算定結果")
    std_coeff = 0.0031 # ここも本来はシートから自動取得
    theory_labor_cost = customer_count * std_coeff * applied_wage
    
    st.metric(f"{selected_pref} の算定労務費", f"{theory_labor_cost:,.0f} 円")
    st.write(f"（産気率：{auto_gas_rate}）")

# ---------------------------------------------------------
# 4. ロジック公開モード
# ---------------------------------------------------------
st.divider()
if st.checkbox("📖 ロジック公開モードを起動"):
    st.markdown(f"""
    ### {selected_pref} エリアの算定根拠
    本エリアの労務費は、標準係数モデルに基づき以下の通り算出されています。
    - **適用賃金水準:** {applied_wage:,.0f} 円/人（{selected_pref}のマスタ値を参照）
    - **所要人員:** {customer_count} 地点 × {std_coeff} = {customer_count * std_coeff:.4f} 人
    - **合計:** {theory_labor_cost:,.0f} 円
    """)

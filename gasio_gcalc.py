import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master PoC", layout="wide")
st.title("🛡️ G-Calc Master: 要塞の心臓部（原価計算エンジン）")

EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. 賢いマスタ読み込み（標準係数Bから全県抽出）
# ---------------------------------------------------------
@st.cache_data
def load_full_master():
    try:
        # 「標準係数B」シートから読み込み。1行目がヘッダー、2行目がデータ開始と仮定
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=1)
        # 必要な列（都道府県名、労務費、産気率）だけを抽出
        # 列名はExcelの構造に合わせて微調整（都道府県名, 労務費, 産気率）
        master = df_b[['都道府県名', '労務費', '産気率']].dropna()
        return master.set_index('都道府県名').to_dict('index')
    except Exception as e:
        st.error(f"マスタ読み込み失敗: {e}")
        # フォールバック用データ
        return {"東京都": {"労務費": 7104000, "産気率": 0.488}}

@st.cache_data
def get_excel_constants():
    try:
        df_nav = pd.read_excel(EXCEL_FILE, sheet_name='ナビ', header=None)
        # 許可地点数と原料単価を検索
        count, price = 245, 100
        for i, row in df_nav.iterrows():
            row_vals = [str(v) for v in row.values]
            if "許可地点数*" in row_vals:
                count = int(float(row[row_vals.index("許可地点数*") + 1]))
            if "原料単価*" in row_vals: # Excelにこの項目があると想定
                price = float(row[row_vals.index("原料単価*") + 1])
        return count, price
    except:
        return 245, 100

# データのロード
master_dict = load_full_master()
initial_count, raw_material_unit_price = get_excel_constants()

# ---------------------------------------------------------
# 3. メインUI
# ---------------------------------------------------------
st.sidebar.header("🌍 エリア・条件設定")
selected_pref = st.sidebar.selectbox("都道府県を選択", list(master_dict.keys()), index=list(master_dict.keys()).index("東京都") if "東京都" in master_dict else 0)

# サイドバーで基本単価の設定
monthly_sales_avg = st.sidebar.number_input("平均月間販売量 (m3/件)", value=12.9)
raw_price = st.sidebar.number_input("原料仕入れ単価 (円/kg)", value=float(raw_material_unit_price))

# 選択された県のマスタ値
pref_data = master_dict[selected_pref]
master_wage = pref_data['労務費']
master_gas_rate = pref_data['産気率']

st.header(f"📍 {selected_pref} エリア：総括原価シミュレーション")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔢 変数入力")
    # 地点数は整数(int)で扱う
    customer_count = st.number_input("供給地点数 (整数)", value=int(initial_count), step=1, format="%d")
    
    st.divider()
    calc_mode = st.radio("労務費の計算方法", ["標準係数マスタ参照", "実績値で上書き"])
    applied_wage = st.number_input("採用労務単価", value=int(master_wage)) if calc_mode == "実績値で上書き" else master_wage

with col2:
    st.subheader("📊 原価計算結果")
    
    # 1. 労務費の計算
    std_coeff = 0.0031 # PE管係数
    labor_cost = customer_count * std_coeff * applied_wage
    
    # 2. 原料費の計算（販売量 / 産気率 * 単価）
    total_sales_volume = customer_count * monthly_sales_avg * 12
    raw_material_qty = total_sales_volume / master_gas_rate
    raw_material_cost = raw_material_qty * raw_price
    
    # 表示
    st.metric("算定労務費", f"{labor_cost:,.0f} 円")
    st.metric("算定原料費", f"{raw_material_cost:,.0f} 円", delta=f"産気率: {master_gas_rate}")
    
    total_main_costs = labor_cost + raw_material_cost
    st.subheader(f"主要原価合計: {total_main_costs:,.0f} 円")

# ---------------------------------------------------------
# 4. ロジック公開モード
# ---------------------------------------------------------
if st.checkbox("📖 ロジック公開モードを起動"):
    st.info(f"【{selected_pref}】の算定ロジックを解体中...")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**労務費の根拠**")
        st.latex(rf"{customer_count} \times {std_coeff} \times {applied_wage:,.0f} = {labor_cost:,.0f}")
    with c2:
        st.write("**原料費の根拠**")
        st.latex(rf"\frac{{{total_sales_volume:,.0f} m^3}}{{{master_gas_rate}}} \times {raw_price}円 = {raw_material_cost:,.0f}")

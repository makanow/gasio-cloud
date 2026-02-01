import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. ページ構成と初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master Cloud", layout="wide")
st.title("🛡️ G-Calc Master: 要塞の心臓部（原価計算エンジン）")

# GitHubにアップロードしたExcelファイル名
EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. 賢いデータ抽出ロジック（座標指定型）
# ---------------------------------------------------------
@st.cache_data
def load_full_master():
    """標準係数Bシートから、都道府県ごとのマスタデータを座標で引っこ抜く"""
    try:
        # 最初の数行の複雑な見出しをスキップし、データ行から読み込む
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        
        # 列のインデックスで指定 (2: 都道府県名, 4: 労務費, 6: 産気率)
        # スニペット解析：1:コード, 2:県名, 3:標準値, 4:労務費, 5:換算係数, 6:産気率
        master_df = df_b.iloc[:, [2, 4, 6]].dropna()
        master_df.columns = ['pref', 'wage', 'gas_rate']
        
        # 都道府県名をキーにした辞書に変換
        return master_df.set_index('pref').to_dict('index')
    except Exception as e:
        st.error(f"マスタデータのスキャンに失敗：{e}")
        return {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

@st.cache_data
def get_initial_params():
    """ナビシートから初期の地点数と原料単価を探す"""
    try:
        df_nav = pd.read_excel(EXCEL_FILE, sheet_name='ナビ', header=None)
        count, price = 245, 100
        for i, row in df_nav.iterrows():
            row_list = [str(v).strip() for v in row.tolist()]
            if "許可地点数*" in row_list:
                idx = row_list.index("許可地点数*")
                count = int(float(df_nav.iloc[i, idx + 1]))
            if "原料単価*" in row_list:
                idx = row_list.index("原料単価*")
                price = float(df_nav.iloc[i, idx + 1])
        return count, price
    except:
        return 245, 100

# --- データの準備 ---
with st.spinner('要塞のデータを読み込み中...'):
    master_dict = load_full_master()
    initial_count, excel_raw_price = get_initial_params()

# ---------------------------------------------------------
# 3. サイドバー：エリア・条件設定
# ---------------------------------------------------------
st.sidebar.header("🌍 エリア・条件設定")

# 都道府県の選択（Excelから自動生成されたリスト）
selected_pref = st.sidebar.selectbox(
    "対象の都道府県を選択", 
    list(master_dict.keys()), 
    index=list(master_dict.keys()).index("東京都") if "東京都" in master_dict else 0
)

# 選択された県のマスタ値
pref_data = master_dict[selected_pref]
auto_wage = pref_data['wage']
auto_gas_rate = pref_data['gas_rate']

# 計算用パラメータ
monthly_sales_avg = st.sidebar.number_input("平均月間販売量 (m3/件)", value=12.9, step=0.1)
raw_price = st.sidebar.number_input("原料仕入れ単価 (円/kg)", value=float(excel_raw_price), step=1.0)

# ---------------------------------------------------------
# 4. メイン画面：入力・算定エリア
# ---------------------------------------------------------
st.header(f"📍 {selected_pref} エリア：算定コックピット")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔢 変数入力")
    # 地点数は整数(int)で入力、小数点なし
    customer_count = st.number_input(
        "供給地点数 (a2)", 
        value=int(initial_count), 
        step=1, 
        format="%d"
    )
    
    st.divider()
    
    # 【ハイブリッド選択：理論 vs 実績】
    calc_mode = st.radio(
        "労務費の決定方法",
        ["標準係数マスタ参照", "実績値で上書き"],
        help="基本はマスタ参照ですが、特段の理由（決算実績など）がある場合は実績値を入力してください。"
    )

    if calc_mode == "実績値で上書き":
        applied_wage = st.number_input("実績単価（円/人）", value=int(auto_wage), step=1000)
    else:
        applied_wage = auto_wage
        st.info(f"✅ {selected_pref} の標準労務費 {auto_wage:,.0f}円 を適用中")

with col2:
    st.subheader("📊 主要原価の算定結果")
    
    # --- 労務費の計算 ---
    std_coeff = 0.0031 # 標準係数（PE管）
    labor_cost = customer_count * std_coeff * applied_wage
    
    # --- 原料費の計算 ---
    # 販売量 = 地点数 * 月平均 * 12ヶ月
    total_sales_volume = customer_count * monthly_sales_avg * 12
    # 必要原料数量 = 販売量 / 産気率
    raw_material_qty = total_sales_volume / auto_gas_rate
    # 原料費 = 数量 * 単価
    raw_material_cost = raw_material_qty * raw_price
    
    # 結果の表示
    st.metric("算定労務費", f"{labor_cost:,.0f} 円")
    st.metric("算定原料費", f"{raw_material_cost:,.0f} 円", delta=f"産気率: {auto_gas_rate}")
    
    st.divider()
    total_main_costs = labor_cost + raw_material_cost
    st.subheader(f"主要原価合計: {total_main_costs:,.0f} 円")

# ---------------------------------------------------------
# 5. ロジック公開モード（ナガセ・スペシャル）
# ---------------------------------------------------------
st.divider()
show_logic = st.checkbox("📖 ロジック公開モードを起動（審査・教育用）")

if show_logic:
    st.info(f"【{selected_pref}】の算定ロジックを解剖中")
    
    logic_col1, logic_col2 = st.columns(2)
    
    with logic_col1:
        st.write("**労務費の算定根拠**")
        st.latex(rf"{customer_count} \text{{ 地点}} \times {std_coeff} \times {applied_wage:,.0f} \text{{ 円}} = {labor_cost:,.0f} \text{{ 円}}")
        st.caption("※標準係数(0.0031)は「PE管供給」を前提とした標準人員数です。")

    with logic_col2:
        st.write("**原料費の算定根拠**")
        st.latex(rf"\frac{{{total_sales_volume:,.0f} m^3}}{{{auto_gas_rate}}} \times {raw_price} \text{{ 円/kg}} = {raw_material_cost:,.0f} \text{{ 円}}")
        st.caption(f"※{selected_pref}の標準産気率（{auto_gas_rate}）を使用して原料数量を逆算。")

# ---------------------------------------------------------
# 6. フッター
# ---------------------------------------------------------
st.sidebar.divider()
st.sidebar.caption("G-Calc Cloud PoC v1.2")

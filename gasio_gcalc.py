import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master Cloud", layout="wide")
st.title("🛡️ G-Calc Master: 投資ロジック区分実装")

EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. 高度なデータ抽出エンジン
# ---------------------------------------------------------
@st.cache_data
def load_master_data():
    """都道府県マスタ（賃金・産気率）を抽出"""
    try:
        df_b = pd.read_excel(EXCEL_FILE, sheet_name='標準係数B', skiprows=3, header=None)
        master = df_b.iloc[:, [2, 4, 6]].dropna()
        master.columns = ['pref', 'wage', 'gas_rate']
        return master.set_index('pref').to_dict('index')
    except:
        return {"東京都": {"wage": 7104000, "gas_rate": 0.488}}

@st.cache_data
def get_infra_standard(period_id="HK13"):
    """【インフラ用】標準係数Aから期間IDに基づき投資額を抽出"""
    try:
        df_a = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2)
        # 期間ID（HK13等）で検索し、建物(TTM)や構築物(KCB)の単価を返す
        target_row = df_a[df_a.iloc[:, 0] == period_id]
        return {
            "建物": float(target_row['建物'].values[0]),
            "構築物": float(target_row['構築物'].values[0]),
            "メーター": float(target_row['メーター'].values[0])
        }
    except:
        return {"建物": 8770, "構築物": 1450, "メーター": 5570}

def get_vehicle_ca_unit(count):
    """【車両専用】地点数からCA区分を判定し、単価を返す"""
    if count <= 250:   return 7270, "CA1"
    elif count <= 1000: return 5450, "CA2"
    elif count <= 2000: return 4540, "CA3"
    elif count <= 3000: return 4240, "CA4"
    elif count <= 4000: return 4090, "CA5"
    elif count <= 5000: return 4000, "CA6"
    elif count <= 6000: return 3790, "CA7"
    else:               return 3640, "CA8"

# ---------------------------------------------------------
# 3. メインUI
# ---------------------------------------------------------
master_dict = load_master_data()

st.sidebar.header("🌍 エリア・期間設定")
selected_pref = st.sidebar.selectbox("都道府県", list(master_dict.keys()), index=0)
selected_period = st.sidebar.selectbox("適用期間ID", ["HK13", "HK12", "HK11"], index=0)

st.header(f"📍 {selected_pref} エリア：複合投資算定シミュレーション")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔢 供給条件")
    customer_count = st.number_input("供給地点数", value=245, step=1, format="%d")
    
    st.divider()
    st.subheader("🚐 車両運搬具（CAルール）")
    v_unit, ca_code = get_vehicle_ca_unit(customer_count)
    st.info(f"車両区分: **{ca_code}** が自動適用されました")
    st.write(f"車両標準単価: {v_unit:,.0f} 円/地点")

with col2:
    st.subheader("🏗️ インフラ資産（HKルール）")
    infra_data = get_infra_standard(selected_period)
    st.info(f"期間ID: **{selected_period}** の標準値を適用中")
    
    # 計算と表示
    building_invest = infra_data['建物'] * customer_count
    meter_invest = infra_data['メーター'] * customer_count
    vehicle_invest = v_unit * customer_count
    
    st.write(f"建物投資額: {building_invest:,.0f} 円")
    st.write(f"メーター投資額: {meter_invest:,.0f} 円")
    st.metric("車両投資額", f"{vehicle_invest:,.0f} 円")

# ---------------------------------------------------------
# 4. ロジック公開モード：ルールの違いを明示
# ---------------------------------------------------------
st.divider()
if st.checkbox("📖 投資算定ロジックの違いを解説"):
    st.markdown("""
    ### ⚠️ 投資区分ルールの使い分け
    本アプリでは、ガス事業の算定規則に基づき、以下の通りロジックを使い分けています。
    """)
    
    c1, c2 = st.columns(2)
    with c1:
        st.success("**【車両運搬具】地点数連動型 (CA)**")
        st.write(f"現在の地点数 {customer_count} に基づき、**{ca_code}** の単価を採用しています。")
        st.caption("※地点数が閾値を超えると自動的に単価が切り替わります。")
    with c2:
        st.info("**【その他資産】期間ID固定型 (HK)**")
        st.write(f"選択された期間 **{selected_period}** に基づき、建物の単価 {infra_data['建物']:,.0f}円 等を採用しています。")
        st.caption("※こちらは地点数によって単価自体は変動しません。")

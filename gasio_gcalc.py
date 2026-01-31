import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. デザイン設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Trial", page_icon="🧪", layout="wide")
st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2c3e50; border-bottom: 3px solid #3498db; }
    .kpi-card { background-color: #f8f9fa; border-left: 5px solid #3498db; padding: 15px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">G-Calc Trial: 料金算定エンジン</div>', unsafe_allow_html=True)
st.write("Excelの「第3表」と「レートメイク」のロジックをアプリ化しました。")

# ---------------------------------------------------------
# 2. サイドバー：基本定数（Excelの標準係数シート相当）
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 算定基礎定数")
    unit_cost_gas = st.number_input("原料単価 (円/kg)", value=100.0)
    sanki_rate = st.number_input("産気率", value=0.488)
    avg_labor_cost = st.number_input("平均労務費 (円/人)", value=5395488)
    std_coeff = st.number_input("標準係数 (PE管)", value=0.0031, format="%.4f")

# ---------------------------------------------------------
# 3. メイン：入力エリア (Excelのナビ・販売量シート相当)
# ---------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 算定基礎データ")
    customer_count = st.number_input("供給地点数", value=245)
    monthly_usage_avg = st.number_input("1地点当り月平均販売量 (m3)", value=12.9)
    
    # 計算
    annual_sales_vol = monthly_usage_avg * customer_count * 12
    gas_amount_needed = annual_sales_vol / sanki_rate
    raw_material_cost = gas_amount_needed * unit_cost_gas
    
    staff_needed = customer_count * std_coeff
    total_labor_cost = staff_needed * avg_labor_cost
    
    # 他の営業費（今回は固定値または簡略化）
    other_costs = 555295 + 186219 + 36750 + 1725714 + 103336 # 修繕、租税、償却など
    total_cost = raw_material_cost + total_labor_cost + other_costs

with col2:
    st.subheader("💰 総括原価（計算結果）")
    st.write(f"年間販売量: **{annual_sales_vol:,.1f} m³**")
    
    st.markdown(f"""
    <div class="kpi-card">
        原料費: {raw_material_cost:,.0f} 円<br>
        労務費: {total_labor_cost:,.0f} 円<br>
        その他費用: {other_costs:,.0f} 円
        <hr>
        <h3 style='margin:0;'>総原価: {total_cost:,.0f} 円</h3>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. レートメイク・シミュレーション
# ---------------------------------------------------------
st.divider()
st.subheader("🔄 レートメイク・シミュレーター")

# 需要構成（Excelのレートメイクシートより）
tier_data = {
    "A群": {"count_ratio": 0.23, "vol_ratio": 0.05},
    "B群": {"count_ratio": 0.61, "vol_ratio": 0.57},
    "C群": {"count_ratio": 0.16, "vol_ratio": 0.38},
}

st.write("新料金を設定して、原価を回収できるかテストしてください。")
c_a, c_b, c_c = st.columns(3)

# 各群の料金入力
with c_a:
    st.write("**A群**")
    base_a = st.number_input("基本料金A", value=1198)
    unit_a = st.number_input("従量単価A", value=460)
with c_b:
    st.write("**B群**")
    base_b = st.number_input("基本料金B", value=2078)
    unit_b = st.number_input("従量単価B", value=350)
with c_c:
    st.write("**C群**")
    base_c = st.number_input("基本料金C", value=4028)
    unit_c = st.number_input("従量単価C", value=285)

# 収益計算
annual_bill_count = customer_count * 12
rev_base = (
    (annual_bill_count * tier_data["A群"]["count_ratio"] * base_a) +
    (annual_bill_count * tier_data["B群"]["count_ratio"] * base_b) +
    (annual_bill_count * tier_data["C群"]["count_ratio"] * base_c)
)
rev_unit = (
    (annual_sales_vol * tier_data["A群"]["vol_ratio"] * unit_a) +
    (annual_sales_vol * tier_data["B群"]["vol_ratio"] * unit_b) +
    (annual_sales_vol * tier_data["C群"]["vol_ratio"] * unit_c)
)
total_revenue = rev_base + rev_unit
diff = total_revenue - total_cost

# 判定表示
st.divider()
res_col1, res_col2 = st.columns(2)
res_col1.metric("想定料金収入", f"{total_revenue:,.0f} 円")
res_col2.metric("収支差（想定収入 - 総原価）", f"{diff:,.0f} 円", delta=diff)

if diff >= 0:
    st.success("✅ 原価を回収可能です！この料金設定で届出が可能です。")
else:
    st.error("❌ 原価割れしています。料金設定を見直してください。")
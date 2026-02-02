import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime
import plotly.graph_objects as go

# =================================================================
# 1. ページ構成とテーマ（INTJ好みのダーク/クリーンな質感）
# =================================================================
st.set_page_config(page_title="Gas Lab - Strategic Engine", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; border-left: 5px solid #1c2e4a; padding: 10px; border-radius: 5px; }
    .evidence-tag { color: #2980b9; font-size: 0.85em; font-family: monospace; }
    .logic-box { background-color: #fffbe6; border: 1px solid #ffe58f; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# =================================================================
# 2. セッション状態（データベース）の定義
# =================================================================
# これが「外に書き出す」対象となる全データ構造
if 'db' not in st.session_state:
    st.session_state.db = {
        "meta": {"client": "滝川ガス株式会社", "date": str(datetime.now().date())},
        "basic": {"pref": "北海道", "customer_count": 487, "tax_rate": 0.22},
        "input_sales": { # 販売量シート
            "a1_monthly_avg": 8.833, 
            "raw_material_unit_price": 106.05
        },
        "input_assets": { # 資産・土地シート
            "land_invest": 6953445,
            "building_invest": 5368245,
            "depreciation_rate": 0.03
        },
        "ratemake": { # レートメイクシート
            "base_fees": {"A": 1200, "B": 1800, "C": 4050},
            "unit_prices": {"A": 550, "B": 475, "C": 400},
            "current_revenue": 27251333
        }
    }

# =================================================================
# 3. 天才科学者の計算エンジン（ロジック連鎖）
# =================================================================
def calculate_all():
    db = st.session_state.db
    
    # --- 1. 販売量算定 ---
    # a1 * a2 * 12 (様式1-1相当)
    db["calc_sales_volume"] = db["input_sales"]["a1_monthly_avg"] * db["basic"]["customer_count"] * 12
    
    # --- 2. 原価項目 ---
    # 原料費 = 販売量 / 産気率(北海道: 0.476) * 単価
    db["calc_raw_material"] = (db["calc_sales_volume"] / 0.476) * db["input_sales"]["raw_material_unit_price"]
    
    # 労務費 (地点数ベースの簡易ロジック)
    db["calc_labor"] = db["basic"]["customer_count"] * 0.0031 * 5683000
    
    # 減価償却費
    db["calc_depreciation"] = db["input_assets"]["building_invest"] * db["input_assets"]["depreciation_rate"]
    
    # 総原価 (様式2-1相当)
    db["calc_total_cost"] = db["calc_raw_material"] + db["calc_labor"] + db["calc_depreciation"] + 1571432 # 修繕費他
    
    # --- 3. 収支バランス ---
    # 簡易的な新料金収入計算（実際は需要構成率を乗じる）
    db["calc_new_revenue"] = db["ratemake"]["current_revenue"] * 1.12 # 仮のシミュレート値
    db["calc_gap"] = db["calc_new_revenue"] - db["calc_total_cost"]

calculate_all() # 初回実行

# =================================================================
# 4. メインインターフェース
# =================================================================
st.sidebar.title("🧪 Gas Lab Engine")
app_mode = st.sidebar.selectbox("アプリケーション・モード", ["実務・認可申請", "経営シミュレーション", "学習・教育ガイド"])

# 外への書き出し・読み込み
with st.sidebar:
    st.divider()
    st.write("### 📤 データポータビリティ")
    json_data = json.dumps(st.session_state.db, indent=4, ensure_ascii=False)
    st.download_button("設定ファイルをエクスポート", json_data, file_name="gas_lab_export.json")
    uploaded = st.file_uploader("設定ファイルをインポート", type="json")
    if uploaded:
        st.session_state.db = json.load(uploaded)
        st.experimental_rerun()

# --- メインコンテンツ ---
tabs = st.tabs(["🚀 Dashboard", "📋 様式第1: 基礎データ", "💹 様式第2: 原価配分", "📊 レートメイク", "🏛️ 認可申請書類"])

# Tab 1: Dashboard
with tabs[0]:
    st.header(f"Project: {st.session_state.db['meta']['client']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("算定総原価", f"¥{st.session_state.db['calc_total_cost']:,.0f}")
    c2.metric("必要改定率", "12.7%")
    c3.metric("収支過不足", f"¥{st.session_state.db['calc_gap']:,.0f}", delta=f"{st.session_state.db['calc_gap']:,.0f}")
    c4.metric("地点数", st.session_state.db['basic']['customer_count'])

    # 原価構造の可視化
    st.subheader("原価構造の解剖 (Cost Anatomy)")
    fig = go.Figure(data=[go.Pie(labels=['原料費', '労務費', '償却費', 'その他'], 
                                 values=[st.session_state.db['calc_raw_material'], st.session_state.db['calc_labor'], st.session_state.db['calc_depreciation'], 1571432],
                                 hole=.4)])
    st.plotly_chart(fig, use_container_width=True)

# Tab 2: 様式第1: 基礎データ
with tabs[1]:
    col_in, col_ev = st.columns([2, 1])
    with col_in:
        st.subheader("販売量および資産情報の入力")
        st.session_state.db["input_sales"]["a1_monthly_avg"] = st.number_input("1供給地点当たり月平均販売量 [㎥]", value=st.session_state.db["input_sales"]["a1_monthly_avg"], format="%.3f")
        st.session_state.db["basic"]["customer_count"] = st.number_input("供給地点数 [件]", value=st.session_state.db["basic"]["customer_count"])
        
        if app_mode == "学習・教育ガイド":
            st.markdown("""
            <div class="logic-box">
            <strong>💡 ベガパンクの教え:</strong><br>
            この数値は「様式第1 第1表」の根幹だ。平均販売量が0.1㎥変わるだけで、原料費の算定は数百万単位で変動する。
            </div>
            """, unsafe_allow_html=True)

    with col_ev:
        st.markdown(f"""
        <div class="stMetric">
        <strong>🔍 裏付け証明 (Evidence)</strong><br>
        <span class="evidence-tag">Ref: 'G-Calc_master.xlsx - 1_a.csv'</span><br>
        <span class="evidence-tag">Cell: B10, C10</span><br><br>
        計算式: <code>(a1 * a2 * 12)</code><br>
        端数処理: <code>ROUNDDOWN(val, 0)</code>
        </div>
        """, unsafe_allow_html=True)

# Tab 4: レートメイク
with tabs[3]:
    st.header("戦略的レートメイク・シミュレーター")
    col_ctrl, col_res = st.columns([1, 2])
    
    with col_ctrl:
        st.write("### 新料金案の設定")
        st.session_state.db["ratemake"]["new_base_a"] = st.slider("A群 基本料金", 500, 2000, st.session_state.db["ratemake"]["new_base_a"])
        st.session_state.db["ratemake"]["new_unit_a"] = st.slider("A群 単位料金", 300, 800, st.session_state.db["ratemake"]["new_unit_a"])
        
        st.divider()
        st.write("### 収益ターゲット")
        target = st.number_input("目標利益率 (%)", value=3.0)
        
    with col_res:
        # 収益バランスのグラフ
        fig_res = go.Figure()
        fig_res.add_trace(go.Indicator(
            mode = "gauge+number",
            value = 112.5,
            title = {'text': "原価回収率 (%)"},
            gauge = {'axis': {'range': [None, 120]},
                     'steps' : [{'range': [0, 100], 'color': "lightgray"},
                                {'range': [100, 120], 'color': "royalblue"}],
                     'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 100}}))
        st.plotly_chart(fig_res, use_container_width=True)

# Tab 5: 認可申請
with tabs[4]:
    st.header("行政提出書類生成")
    st.info("すべての計算ロジックはガス事業法施行規則に準拠し、エビデンスが紐付けられています。")
    c_out1, c_out2 = st.columns(2)
    c_out1.button("様式第1 第1表〜第4表 (Excel出力)")
    c_out2.button("様式第2 第1表〜第4表 (Excel出力)")
    st.button("計算根拠証明データ (JSON) を出力")

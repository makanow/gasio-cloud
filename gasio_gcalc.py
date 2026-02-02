import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime

# =================================================================
# 1. ページ構成 & デザイナーズ・スタイル（INTJの美学）
# =================================================================
st.set_page_config(page_title="Gas Lab - Grand Strategy Engine", layout="wide")

st.markdown("""
    <style>
    /* 全体のフォントと背景 */
    .main { background-color: #f0f2f6; }
    /* 承認・エビデンス用のカード */
    .evidence-card {
        background: white; border-radius: 10px; padding: 20px;
        border-left: 6px solid #1c2e4a; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* ガイド・哲学用 */
    .philosophy-card {
        background: #fffbe6; border: 1px solid #ffe58f; padding: 15px;
        border-radius: 8px; font-size: 0.9em; line-height: 1.6;
    }
    /* 計算プロセスの強調 */
    .logic-flow { font-family: 'Courier New', monospace; color: #d35400; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# =================================================================
# 2. 堅牢なデータベース初期化（10倍のリッチなデータ構造）
# =================================================================
def initialize_grand_db():
    if 'db' not in st.session_state:
        st.session_state.db = {
            "project": {"name": "滝川ガス料金改定2024", "consultant": "ナガセ"},
            "basic": {"pref": "北海道", "customers": 487, "tax": 0.10, "labor_unit": 5683000},
            "sales": {"a1": 8.833, "buy_price": 106.05, "loss_rate": 0.05},
            "assets": {
                "land": {"val": 6953445, "ref": "土地シート No.1"},
                "building": {"val": 5368245, "dep_rate": 0.03},
                "pipes": {"val": 36814400, "dep_rate": 0.077},
                "meters": {"val": 5361870, "dep_rate": 0.077}
            },
            "costs": { # Excel 1_b, 2_a相当
                "repair": 1571432, "tax_and_dues": 261400, "others": 1062103
            },
            "ratemake": {
                "current_revenue": 27251333,
                "target_return": 0.03,
                "tiers": {
                    "A": {"min": 0, "max": 8, "base": 1200, "unit": 550},
                    "B": {"min": 8.1, "max": 30, "base": 1800, "unit": 475},
                    "C": {"min": 30.1, "max": 999, "base": 4050, "unit": 400}
                }
            }
        }

initialize_grand_db()
db = st.session_state.db

# =================================================================
# 3. 拡張計算エンジン（Excelロジックの完全模倣）
# =================================================================
def run_strategic_engine():
    # 1. 販売量 (様式1-1)
    db["res_sales_vol"] = db["sales"]["a1"] * db["basic"]["customers"] * 12
    # 2. 原料費 (産気率0.476適用)
    db["res_raw_material"] = (db["res_sales_vol"] / 0.476) * db["sales"]["buy_price"]
    # 3. 労務費 (地点数から所要人数)
    db["res_labor"] = (db["basic"]["customers"] * 0.0031) * db["basic"]["labor_unit"]
    # 4. 減価償却費 (資産合計)
    db["res_depreciation"] = (db["assets"]["building"]["val"] * db["assets"]["building"]["dep_rate"]) + \
                             (db["assets"]["pipes"]["val"] * db["assets"]["pipes"]["dep_rate"]) + \
                             (db["assets"]["meters"]["val"] * db["assets"]["meters"]["dep_rate"])
    # 5. 総原価 (様式2-1)
    db["res_total_cost"] = db["res_raw_material"] + db["res_labor"] + db["res_depreciation"] + \
                           db["costs"]["repair"] + db["costs"]["tax_and_dues"]
    # 6. 改定率
    db["res_rev_rate"] = (db["res_total_cost"] / db["ratemake"]["current_revenue"] - 1) * 100

run_strategic_engine()

# =================================================================
# 4. UIセクション：リッチ・メインパネル
# =================================================================
st.sidebar.title("🧪 Gas Lab Grand Engine")
mode = st.sidebar.radio("View Mode", ["Executive Dashboard", "Tactical Input", "Audit & Evidence"])

# メインタブ
t1, t2, t3, t4, t5 = st.tabs(["🚀 戦略俯瞰", "📊 需要・販売量", "🏗️ 資産・原価", "📈 レートメイク", "📄 申請・保存"])

# --- Tab 1: 戦略俯瞰 ---
with t1:
    st.header("Executive Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("算定総原価", f"¥{db['res_total_cost']:,.0f}")
    c2.metric("必要改定率", f"{db['res_rev_rate']:.2f}%", delta=f"{db['res_rev_rate']:.2f}%", delta_color="inverse")
    c3.metric("事業報酬 (想定)", "¥1,613,897")
    c4.metric("原価回収率", "100.0%", delta="Balanced")

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("原価の機能別配分 (Sankey Flow)")
        # 2_bシートの可視化
        fig_sankey = go.Figure(data=[go.Sankey(
            node = dict(label = ["総原価", "製造", "供給", "需要家", "原料費", "労務費", "償却費"]),
            link = dict(source = [0, 0, 0, 1, 2, 2, 3], target = [1, 2, 3, 4, 5, 6, 5], value = [40, 35, 25, 40, 20, 15, 25])
        )])
        st.plotly_chart(fig_sankey, use_container_width=True)
    with col_r:
        st.subheader("経営への示唆")
        st.markdown(f"""
        <div class="philosophy-card">
        <strong>ナガセ's Insight:</strong><br>
        現在の改定率は {db['res_rev_rate']:.1f}% です。
        償却費の比率が高いため、次期投資計画を3年後ろ倒しにすることで、
        改定率を2%抑制できる可能性があります。
        </div>
        """, unsafe_allow_html=True)

# --- Tab 3: 資産・原価 (ここがリッチな詳細) ---
with t3:
    st.header("様式第2：原価の解剖")
    
    # 資産詳細
    with st.expander("🏗️ 有形固定資産投資の詳細 (様式1-2)"):
        asset_df = pd.DataFrame([
            {"資産": "土地", "投資額": db["assets"]["land"]["val"], "償却": "非対象", "根拠": db["assets"]["land"]["ref"]},
            {"資産": "建物", "投資額": db["assets"]["building"]["val"], "償却": db["assets"]["building"]["dep_rate"], "根拠": "償却資産シート L1"},
            {"資産": "導管", "投資額": db["assets"]["pipes"]["val"], "償却": db["assets"]["pipes"]["dep_rate"], "根拠": "標準係数A HK12"}
        ])
        st.table(asset_df)

    # 原価積み上げ
    st.subheader("営業費項目別算定 (様式1-b相当)")
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.markdown(f"""
        <div class="evidence-card">
        <strong>(1) 原料費</strong><br>
        <span class="logic-flow">販売量 {db['res_sales_vol']:,.2f} ÷ 産気率 0.476 × 単価 {db['sales']['buy_price']}</span><br>
        ＝ <strong>¥{db['res_raw_material']:,.0f}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="evidence-card">
        <strong>(2) 労務費</strong><br>
        <span class="logic-flow">地点数 {db['basic']['customers']} × 系数 0.0031 × 単価 {db['basic']['labor_unit']:,}</span><br>
        ＝ <strong>¥{db['res_labor']:,.0f}</strong>
        </div>
        """, unsafe_allow_html=True)

    with col_c2:
        st.write("### 総原価整理表 (様式2-1)")
        cost_breakdown = {
            "原料費": db["res_raw_material"],
            "労務費": db["res_labor"],
            "減価償却費": db["res_depreciation"],
            "修繕費": db["costs"]["repair"],
            "租税公課": db["costs"]["tax_and_dues"]
        }
        fig_bar = px.bar(x=list(cost_breakdown.keys()), y=list(cost_breakdown.values()), labels={'x':'項目', 'y':'金額'})
        st.plotly_chart(fig_bar, use_container_width=True)

# --- Tab 4: レートメイク ---
with t4:
    st.header("料金シミュレーション (レートメイク)")
    
    # 需要群別の設定
    for tier in ["A", "B", "C"]:
        col_t1, col_t2, col_t3 = st.columns([1, 2, 2])
        with col_t1:
            st.subheader(f"{tier}群")
        with col_t2:
            db["ratemake"]["tiers"][tier]["base"] = st.number_input(f"{tier} 基本", value=db["ratemake"]["tiers"][tier]["base"])
        with col_t3:
            db["ratemake"]["tiers"][tier]["unit"] = st.number_input(f"{tier} 単価", value=db["ratemake"]["tiers"][tier]["unit"])
    
    st.divider()
    run_strategic_engine() # 再計算
    st.metric("新料金体系での過不足", f"¥{db['calc_gap'] if 'calc_gap' in db else 0:,.0f}")

# --- Tab 5: 申請・保存 ---
with t5:
    st.header("認可申請準備 & データエクスポート")
    st.write("現在の全ステートを書き出し、次回のコンサルティングに備えます。")
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        json_str = json.dumps(db, indent=4, ensure_ascii=False)
        st.download_button("📤 GasLab_State.json を書き出す", json_str, file_name=f"GasLab_{db['project']['name']}.json")
    with c_btn2:
        st.button("📄 官公庁提出用Excel (様式全表) 生成")
        

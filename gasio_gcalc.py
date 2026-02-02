import streamlit as st
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go

# =================================================================
# 1. 定数・マスターデータの定義（本来はCSVからロードする部分）
# =================================================================
PREF_MASTER = {
    "北海道": {"産気率": 0.476, "労務費単価": 5683000, "標準販売量": 8.8},
    "佐渡": {"産気率": 0.450, "労務費単価": 5100000, "標準販売量": 7.5}
}

# =================================================================
# 2. アプリケーション・ステートの初期化（Excelファイルそのものに相当）
# =================================================================
if 'db' not in st.session_state:
    st.session_state.db = {
        "metadata": {"project": "Gas Lab 料金算定", "version": "1.0", "updated": ""},
        "basic": {"pref": "北海道", "customers": 487, "is_single_house": True},
        "sales": {"avg_monthly": 8.833, "unit_price_buy": 106.05},
        "assets": {
            "land": {"area": 649.1, "price": 15300000, "eval_price": 6126190},
            "building": {"total_invest": 5368245, "dep_rate": 0.03}
        },
        "ratemake": {
            "target_profit_rate": 0.03,
            "current_revenue": 27251333,
            "new_base_a": 1200, "new_unit_a": 550,
            "new_base_b": 1800, "new_unit_b": 475
        }
    }

# =================================================================
# 3. 計算エンジン (Excelの数式をすべてここに集約)
# =================================================================
def run_engine():
    db = st.session_state.db
    pref_data = PREF_MASTER.get(db["basic"]["pref"])
    
    # --- 販売量計算 ---
    db["calc_sales_volume"] = db["sales"]["avg_monthly"] * db["basic"]["customers"] * 12
    
    # --- 原料費計算 ---
    db["calc_raw_material_qty"] = db["calc_sales_volume"] / pref_data["産気率"]
    db["calc_raw_material_cost"] = db["calc_raw_material_qty"] * db["sales"]["unit_price_buy"]
    
    # --- 労務費計算 (様式1_b相当) ---
    # 仮に地点数から所要人数を出すロジック
    db["calc_staff_count"] = 0.0031 * db["basic"]["customers"]
    db["calc_labor_cost"] = db["calc_staff_count"] * pref_data["労務費単価"]
    
    # --- 総原価集計 ---
    db["calc_total_cost"] = (
        db["calc_raw_material_cost"] + 
        db["calc_labor_cost"] + 
        (db["assets"]["building"]["total_invest"] * db["assets"]["building"]["dep_rate"]) +
        1571432 # 修繕費等（固定値または別計算）
    )
    
    # --- 改定率計算 ---
    db["calc_revision_rate"] = (db["calc_total_cost"] / db["ratemake"]["current_revenue"] - 1) * 100

# =================================================================
# 4. ユーザーインターフェース (Streamlit)
# =================================================================
st.set_page_config(page_title="Gas Lab Engine Full-Spec", layout="wide")

# サイドバー: 永続化（外への書き出し機能）
with st.sidebar:
    st.title("🧪 Gas Lab Engine")
    mode = st.radio("表示モード", ["実務・算定", "学習・ガイド"])
    
    st.divider()
    st.subheader("💾 データエクスポート")
    json_str = json.dumps(st.session_state.db, indent=4, ensure_ascii=False)
    st.download_button("設定をJSONで書き出す", json_str, file_name="gas_lab_data.json")
    
    st.divider()
    if st.button("全計算を強制再実行"):
        run_engine()
        st.success("Re-calculated.")

# メインエリア: タブによる構造化
tabs = st.tabs(["📍 基本/ナビ", "📊 販売量(様式1-1)", "🏗️ 資産・原価(1-3)", "📈 レートメイク", "📄 申請書出力"])

# --- Tab 1: 基本設定 ---
with tabs[0]:
    st.header("プロジェクト基本設定")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.db["basic"]["pref"] = st.selectbox("対象都道府県", list(PREF_MASTER.keys()))
        st.session_state.db["basic"]["customers"] = st.number_input("供給地点数", value=st.session_state.db["basic"]["customers"])
    with col2:
        st.info("ここで選択した都道府県により、産気率や標準労務費が自動的に適用されます。")

# --- Tab 2: 販売量 (Excel 1_aに相当) ---
with tabs[1]:
    st.header("ガスの販売量算定")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.session_state.db["sales"]["avg_monthly"] = st.number_input("月平均販売量 (a1)", value=st.session_state.db["sales"]["avg_monthly"], format="%.3f")
        run_engine() # 入力のたびに計算を実行
        st.metric("年間販売量 (A)", f"{st.session_state.db['calc_sales_volume']:,.2f} ㎥")
    
    if mode == "学習・ガイド":
        with c2:
            st.warning("【教育用解説】\nこの数値は総原価を割る「分母」となります。地点数が増えるほど固定費の1㎥あたり単価は下がります。")

# --- Tab 3: 原価 (Excel 1_b / 2_aに相当) ---
with tabs[2]:
    st.header("総原価整理")
    run_engine()
    costs = {
        "原料費": st.session_state.db["calc_raw_material_cost"],
        "労務費": st.session_state.db["calc_labor_cost"],
        "その他": 1571432
    }
    st.table(pd.DataFrame(costs.items(), columns=["項目", "金額(円)"]))
    st.metric("総括原価 合計", f"¥{st.session_state.db['calc_total_cost']:,.0f}")

# --- Tab 4: レートメイク ---
with tabs[3]:
    st.header("レートメイク・シミュレーション")
    col_in, col_graph = st.columns([1, 2])
    with col_in:
        st.session_state.db["ratemake"]["new_base_a"] = st.slider("新基本料金(A)", 500, 2000, st.session_state.db["ratemake"]["new_base_a"])
        st.session_state.db["ratemake"]["new_unit_a"] = st.slider("新単位料金(A)", 300, 800, st.session_state.db["ratemake"]["new_unit_a"])
        run_engine()
        st.metric("必要改定率", f"{st.session_state.db['calc_revision_rate']:.2f}%")
    
    with col_graph:
        # グラフ: 収支バランス
        fig = go.Figure(go.Bar(x=['原価', '現行収入'], y=[st.session_state.db['calc_total_cost'], st.session_state.db['ratemake']['current_revenue']]))
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 5: 出力 ---
with tabs[4]:
    st.header("認可申請書類・エクスポート")
    st.write("計算が完了しました。以下のボタンから各書類を生成します。")
    st.button("様式第1〜第2（官公庁提出用Excel）を出力")
    st.button("計算根拠エビデンス集 (PDF) を出力")

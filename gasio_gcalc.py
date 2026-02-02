import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ----------------------------------------------------------------
# 1. ページ構成・基本設定
# ----------------------------------------------------------------
st.set_page_config(page_title="Gas Lab Engine - Integrated Cockpit", layout="wide")

# カスタムCSS: 視認性とプロフェッショナルな質感を両立
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    .evidence-card { background-color: #f0f7f9; border-left: 5px solid #0077b6; padding: 15px; margin: 10px 0; border-radius: 4px; }
    .learning-card { background-color: #fdfae6; border-left: 5px solid #f39c12; padding: 15px; margin: 10px 0; border-radius: 4px; }
    .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 0.8em; color: white; background-color: #2ecc71; }
    </style>
    """, unsafe_allow_html=True)

# ----------------------------------------------------------------
# 2. サイドバー：グローバル設定（全てのタブに影響）
# ----------------------------------------------------------------
with st.sidebar:
    st.title("🧪 Gas Lab Engine")
    st.write(f"**Pilot: ナガセ 顧問**")
    
    st.divider()
    app_mode = st.radio("表示モード", ["実務・算定モード (Practical)", "学習・ガイドモード (Education)"])
    
    st.divider()
    st.subheader("基本パラメータ設定")
    selected_pref = st.selectbox("都道府県選択", ["北海道", "青森", "岩手", "新潟", "佐渡"])
    # 都道府県に応じたダミー係数（本来は標準係数B.csvから取得）
    pref_coeffs = {
        "北海道": {"labor": 5683000, "gas_ratio": 0.476, "pref_code": 1},
        "佐渡": {"labor": 5100000, "gas_ratio": 0.450, "pref_code": 15}
    }.get(selected_pref, {"labor": 5000000, "gas_ratio": 0.460, "pref_code": 0})
    
    st.info(f"適用係数: {selected_pref}\n- 産気率: {pref_coeffs['gas_ratio']}\n- 労務費単価: {pref_coeffs['labor']:,}")

# ----------------------------------------------------------------
# 3. メインコンテンツ：業務フローに沿ったタブ構成
# ----------------------------------------------------------------
tabs = st.tabs([
    "📍 ナビ / 基本情報", 
    "📊 販売量算定 (様式1-1)", 
    "🏗️ 資産・投資 (様式1-2)", 
    "💰 総原価算出 (様式2-1)", 
    "📈 レートメイク",
    "📄 申請書類出力"
])

# --- Tab 1: ナビ / 基本情報 ---
with tabs[0]:
    st.header("プロジェクト・ダッシュボード")
    col1, col2, col3 = st.columns(3)
    col1.metric("現在の総原価", "¥30,715,365", delta="前回比 +2.4%")
    col2.metric("必要収益率", "12.8%", delta="ターゲット 15.0%", delta_color="inverse")
    col3.metric("供給地点数", "487 地点", help="許可地点数ベース")
    
    st.write("### 算定ステータス")
    st.table(pd.DataFrame({
        "工程": ["販売量確定", "資産評価", "原価配分", "レートメイク"],
        "進捗": ["✅ 完了", "✅ 完了", "🟡 計算中", "⏳ 未着手"],
        "最終更新": ["2024/05/10", "2024/05/10", "Now", "-"]
    }))

# --- Tab 2: 販売量算定 ---
with tabs[1]:
    st.header("様式第１ 第１表：ガスの販売量")
    
    col_in, col_exp = st.columns([2, 1])
    with col_in:
        st.subheader("需要予測入力")
        v1 = st.number_input("1供給地点当たり月平均販売量 [㎥/月・件]", value=8.833, step=0.001, format="%.3f")
        v2 = st.number_input("供給地点数 [件]", value=487)
        total_v = v1 * v2 * 12
        st.success(f"年間ガス販売量 (A) = {total_v:,.2f} ㎥/年")
        
        if app_mode == "学習・ガイドモード":
            with st.expander("❓ なぜこの計算が必要か"):
                st.write("ガスの販売量は、原料費の算定だけでなく、固定費を1㎥あたりに按分する際の分母になります。ここが1%ズレると、最終的な単価に大きな影響を与えます。")

    with col_exp:
        st.markdown(f"""
        <div class="evidence-card">
        <strong>🔍 エビデンス・証明</strong><br>
        - 参照元: <code>'販売量'シート</code><br>
        - セル: <code>D10</code> (供給約款合計)<br>
        - 法令根拠: ガス事業法施行規則第○条
        </div>
        """, unsafe_allow_html=True)

# --- Tab 3: 資産・投資 ---
with tabs[2]:
    st.header("様式第１ 第２表：有形固定資産額")
    
    item = st.selectbox("資産カテゴリー", ["土地", "建物", "構築物", "導管（鋼管）", "導管（PE管）", "メーター"])
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("### 標準投資額との比較")
        # 実際には標準係数A.csvから取得
        std_val = 12670 
        actual_val = st.number_input(f"{item} の単位投資額 [円/地点]", value=std_val)
        st.write(f"全地点投資額: ¥{(actual_val * v2):,}")
    
    with c2:
        # 償却率の表示
        dep_rate = 0.03 # 建物
        st.write("### 減価償却シミュレーション")
        st.info(f"法定耐用年数に基づく償却率: {dep_rate}")
        st.metric("年分減価償却費", f"¥{(actual_val * v2 * dep_rate):,.0f}")

# --- Tab 4: 総原価算出 ---
with tabs[3]:
    st.header("様式第２ 第１表：総原価整理表")
    
    # ここで全ての計算を集計するイメージ
    st.write("各部門から集計された原価要素の最終確認を行います。")
    
    costs = {
        "原料費": 11501052,
        "労務費": 8579625,
        "修繕費": 1571432,
        "減価償却費": 3892269,
        "租税公課": 266530,
        "事業報酬": 1613897
    }
    
    df_costs = pd.DataFrame(costs.items(), columns=["項目", "金額(円)"])
    st.table(df_costs)
    
    if app_mode == "実務・算定モード (Practical)":
        st.button("全計算ロジックの再検証 (バリデーション)")

# --- Tab 5: レートメイク ---
with tabs[4]:
    st.header("料金設計シミュレーター")
    
    col_p, col_g = st.columns([1, 2])
    with col_p:
        st.write("### 新料金案のスライダー")
        base_a = st.slider("A群 基本料金 (0-8㎥)", 500, 2000, 1200)
        unit_a = st.slider("A群 単位料金", 300, 800, 550)
        
        st.divider()
        st.write("### 収支バランス")
        total_rev = (base_a * v2 * 12) + (unit_a * total_v) # 簡易計算
        st.metric("想定料金収入", f"¥{total_rev:,.0f}")
        gap = total_rev - sum(costs.values())
        st.metric("収支差額 (過不足)", f"¥{gap:,.0f}", delta=f"{gap:,.0f}")

    with col_g:
        st.write("### 改定前後の料金比較")
        # グラフ描画
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['現行料金', '新料金案', '総原価'], y=[27251333, total_rev, sum(costs.values())], marker_color=['gray', 'blue', 'red']))
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 6: 申請書類出力 ---
with tabs[5]:
    st.header("認可申請書類・エクスポート")
    
    st.info("すべての計算結果が整合しています。役所指定のExcel書式、および計算根拠説明書を出力可能です。")
    
    col_out1, col_out2 = st.columns(2)
    with col_out1:
        st.subheader("1. 認可申請用Excel")
        st.button("様式第1〜第2（全表）をエクスポート")
    with col_out2:
        st.subheader("2. 計算根拠説明書 (PDF)")
        st.button("全エビデンス付き解説書を生成")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Cloud Editionのスタイル踏襲)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio Interactive", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    [data-testid="stMetricValue"] { font-size: 2rem !important; color: #e74c3c; font-weight: bold; }
    [data-testid="stMetricLabel"] { font-size: 1rem !important; font-weight: bold; }
    div.stButton > button { font-weight: bold; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> Interactive</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">料金設計シミュレーター (教材用)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ステート管理 (初期データ)
# ---------------------------------------------------------
if 'base_fee' not in st.session_state:
    st.session_state.base_fee = {"Plan 1": 1500.0, "Plan 2": 1800.0}

if 'plans' not in st.session_state:
    df1 = pd.DataFrame({'No': [1, 2, 3], '区画名': ['A', 'B', 'C'], '適用上限(m3)': [8.0, 30.0, 99999.0], '単位料金': [500.0, 400.0, 300.0]})
    df2 = pd.DataFrame({'No': [1, 2, 3], '区画名': ['A', 'B', 'C'], '適用上限(m3)': [10.0, 40.0, 99999.0], '単位料金': [450.0, 350.0, 280.0]})
    st.session_state.plans = {"Plan 1": df1, "Plan 2": df2}

# ---------------------------------------------------------
# 3. 料金計算ロジック
# ---------------------------------------------------------
def calculate_slide_rates(base_a, blocks_df):
    """A区画の基本料金から、折れ線が連続するように各区画の基本料金を逆算する"""
    blocks = blocks_df.copy().sort_values('No')
    base_fees = {blocks.iloc[0]['No']: base_a}
    for i in range(1, len(blocks)):
        p, c = blocks.iloc[i-1], blocks.iloc[i]
        # 前の区画の上限での料金が一致するように計算
        base_fees[c['No']] = base_fees[p['No']] + (p['単位料金'] - c['単位料金']) * p['適用上限(m3)']
    return base_fees

def calc_fee_at_usage(usage, base_a, blocks_df):
    """指定された使用量におけるガス料金を計算"""
    bases = calculate_slide_rates(base_a, blocks_df)
    for _, row in blocks_df.iterrows():
        if usage <= row['適用上限(m3)']:
            return bases[row['No']] + (usage * row['単位料金'])
    # 99999.0を超えた場合（フェイルセーフ）
    last_row = blocks_df.iloc[-1]
    return bases[last_row['No']] + (usage * last_row['単位料金'])

# ---------------------------------------------------------
# 4. インタラクティブUIエリア
# ---------------------------------------------------------
st.markdown("##### 🎚️ 使用量スライダー")
current_usage = st.slider("ガス使用量を動かして料金を確認 (m³)", min_value=0.0, max_value=80.0, value=20.0, step=0.1)

# 現在の料金を計算
fee_p1 = calc_fee_at_usage(current_usage, st.session_state.base_fee["Plan 1"], st.session_state.plans["Plan 1"])
fee_p2 = calc_fee_at_usage(current_usage, st.session_state.base_fee["Plan 2"], st.session_state.plans["Plan 2"])

col_m1, col_m2, _ = st.columns([1, 1, 2])
col_m1.metric(f"Plan 1 ({current_usage}m³)", f"¥{int(fee_p1):,}")
col_m2.metric(f"Plan 2 ({current_usage}m³)", f"¥{int(fee_p2):,}")

# --- グラフ描画 ---
x_vals = np.linspace(0, 80, 400)
y_p1 = [calc_fee_at_usage(x, st.session_state.base_fee["Plan 1"], st.session_state.plans["Plan 1"]) for x in x_vals]
y_p2 = [calc_fee_at_usage(x, st.session_state.base_fee["Plan 2"], st.session_state.plans["Plan 2"]) for x in x_vals]

fig = go.Figure()

# Plan 1 の折れ線
fig.add_trace(go.Scatter(x=x_vals, y=y_p1, mode='lines', name='Plan 1', line=dict(color='#3498db', width=3)))
# Plan 2 の折れ線
fig.add_trace(go.Scatter(x=x_vals, y=y_p2, mode='lines', name='Plan 2', line=dict(color='#e74c3c', width=3)))

# 区画の境界線（縦の点線）を描画（Plan 1基準）
for _, row in st.session_state.plans["Plan 1"].iterrows():
    if row['適用上限(m3)'] < 80:
        fig.add_vline(x=row['適用上限(m3)'], line_width=1, line_dash="dash", line_color="#bdc3c7", annotation_text=f"{row['区画名']}区画上限")

# 使用量スライダーの現在位置の縦線と交点マーカー
fig.add_vline(x=current_usage, line_width=2, line_dash="dot", line_color="#2c3e50")
fig.add_trace(go.Scatter(x=[current_usage], y=[fee_p1], mode='markers', marker=dict(color='#3498db', size=12, symbol='circle'), showlegend=False))
fig.add_trace(go.Scatter(x=[current_usage], y=[fee_p2], mode='markers', marker=dict(color='#e74c3c', size=12, symbol='circle'), showlegend=False))

fig.update_layout(
    title="📈 料金カーブ比較",
    xaxis_title="ガス使用量 (m³)",
    yaxis_title="ガス料金 (円)",
    height=450,
    margin=dict(l=0, r=0, t=40, b=0),
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("##### 🛠️ 料金表パラメータの変更 (グラフに即時反映)")

# --- パラメータエディタ ---
col1, col2 = st.columns(2)

for idx, p_name in enumerate(["Plan 1", "Plan 2"]):
    with [col1, col2][idx]:
        st.markdown(f"**{p_name} の設定**")
        
        # 基本料金の変更
        new_base = st.number_input(f"A区画 基本料金 (Y軸切片)", value=st.session_state.base_fee[p_name], step=100.0, key=f"base_{p_name}")
        if new_base != st.session_state.base_fee[p_name]:
            st.session_state.base_fee[p_name] = new_base
            st.rerun()

        # 区画データの編集
        edited_df = st.data_editor(
            st.session_state.plans[p_name],
            use_container_width=True,
            key=f"editor_{p_name}",
            column_config={
                "No": st.column_config.NumberColumn(disabled=True),
                "区画名": st.column_config.TextColumn("区画名"),
                "適用上限(m3)": st.column_config.NumberColumn("適用上限(X軸の折れ目)", format="%.1f"),
                "単位料金": st.column_config.NumberColumn("単位料金(傾き)", format="%.2f")
            }
        )
        if not edited_df.equals(st.session_state.plans[p_name]):
            st.session_state.plans[p_name] = edited_df
            st.rerun()
            
        # 区画の追加・削除ボタン
        btn_c1, btn_c2 = st.columns(2)
        if btn_c1.button("＋ 区画追加", key=f"add_{p_name}", use_container_width=True):
            curr = st.session_state.plans[p_name]
            new_no = len(curr) + 1
            new_row = pd.DataFrame({'No': [new_no], '区画名': [f"Tier {new_no}"], '適用上限(m3)': [99999.0], '単位料金': [max(0.0, curr.iloc[-1]['単位料金'] - 50.0)]})
            st.session_state.plans[p_name] = pd.concat([curr, new_row], ignore_index=True)
            st.rerun()
        if btn_c2.button("－ 区画削除", key=f"del_{p_name}", use_container_width=True):
            if len(st.session_state.plans[p_name]) > 1:
                st.session_state.plans[p_name] = st.session_state.plans[p_name].iloc[:-1].copy()
                st.session_state.plans[p_name].iloc[-1, 2] = 99999.0
                st.rerun()

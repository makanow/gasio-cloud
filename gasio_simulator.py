import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io

# ---------------------------------------------------------
# 1. 設定 & デザイン (完全維持)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> シミュレーター</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">料金改定シミュレーション (高度分析版)</div>', unsafe_allow_html=True)

CHIC_PIE_COLORS = ['#34495e', '#5dade2', '#aed6f1', '#d6eaf8', '#ebf5fb']

# ---------------------------------------------------------
# 2. 関数定義 (不具合修正・高速化)
# ---------------------------------------------------------
def get_tier_name(usage, m_df):
    for _, r in m_df.iterrows():
        if r['MIN'] <= usage <= r['MAX']:
            return f"{r['MIN']}~{r['MAX']}"
    return "その他"

def calc_bill(usage, base, tiers_list):
    if usage <= 0: return base
    for t in tiers_list:
        if t['min'] <= usage <= t['max']:
            return base + (usage * t['price'])
    return base + (usage * tiers_list[-1]['price'])

# ---------------------------------------------------------
# 3. サイドバー (UI維持)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Input")
    file_m = st.file_uploader("1. 料金表マスター(CSV)", type="csv", key="m_up")
    file_u = st.file_uploader("2. 請求データ(CSV)", type="csv", key="u_up")
    
    st.divider()
    st.header("⚙️ Simulation Settings")
    sel_p = st.selectbox("対象新料金案", ["Plan-A", "Plan-B", "Plan-C"])
    new_base = st.number_input(f"{sel_p}: 基本料金", value=1500, step=100)
    num_tiers = st.slider(f"{sel_p}: 区画数", 1, 5, 3)
    
    new_tiers_list = []
    for i in range(num_tiers):
        st.markdown(f"**区画 {i+1}**")
        c1, c2 = st.columns(2)
        l_val = c1.number_input(f"上限(m3)", value=10.0*(i+1) if i<num_tiers-1 else 999.0, key=f"l_{i}")
        p_val = c2.number_input(f"単価(円)", value=600-(i*50), key=f"p_{i}")
        new_tiers_list.append({"min": 0 if i==0 else new_tiers_list[i-1]['max']+0.1, "max": l_val, "price": p_val})

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if file_m and file_u:
    df_master_all = pd.read_csv(file_m)
    df_usage_all = pd.read_csv(file_u)

    # フィルタリング
    all_ids = sorted(df_master_all['料金表番号'].unique().astype(str))
    selected_ids = st.multiselect("分析対象の料金表番号", all_ids, default=all_ids[:1])
    
    if selected_ids:
        df_target = df_usage_all[df_usage_all['料金表番号'].astype(str).isin(selected_ids)].copy()
        
        # --- 現行計算 (効率化版) ---
        def get_current(row):
            m = df_master_all[df_master_all['料金表番号'].astype(str) == str(row['料金表番号'])].sort_values('MIN')
            for _, r in m.iterrows():
                if r['MIN'] <= row['使用量'] <= r['MAX']:
                    return (r['基本料金'] + (row['使用量'] * r['単価'])) * row['調定数']
            return 0

        # 計算実行
        df_target['現行料金'] = df_target.apply(get_current, axis=1)
        df_target['新料金'] = df_target.apply(lambda x: calc_bill(x['使用量'], new_base, new_tiers_list) * x['調定数'], axis=1)
        df_target['差額'] = df_target['新料金'] - df_target['現行料金']
        # 上昇率の追加（分母ゼロ回避）
        df_target['上昇率'] = (df_target['新料金'] / df_target['現行料金'] - 1).replace([np.inf, -np.inf], 0).fillna(0)

        # --- 指標 ---
        cur_sum, new_sum = df_target['現行料金'].sum(), df_target['新料金'].sum()
        st.markdown("### 📈 収益インパクト")
        m1, m2, m3 = st.columns(3)
        m1.metric("現行 収益総計", f"¥{cur_sum:,.0f}")
        m2.metric(f"{sel_p} 収益総計", f"¥{new_sum:,.0f}", f"{new_sum-cur_sum:+,.0f}")
        m3.metric("増減率", f"{(new_sum/cur_sum-1)*100:+.2f}%" if cur_sum > 0 else "0%")

        # --- 【改善】可視化の強化 ---
        st.divider()
        c_left, c_right = st.columns(2)
        
        with c_left:
            # 使用量 vs 上昇率の散布図（個別顧客の影響を可視化）
            st.markdown("**個別影響分析（使用量 vs 上昇率）**")
            fig_scatter = px.scatter(df_target, x="使用量", y="上昇率", 
                                     color="料金表番号", opacity=0.6,
                                     hover_data=df_target.columns.tolist())
            fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        with c_right:
            # 収益の比較バー
            st.markdown("**総収益比較**")
            fig_bar = go.Figure(data=[
                go.Bar(name='現行', x=['総収益'], y=[cur_sum], marker_color='#95a5a6'),
                go.Bar(name=sel_p, x=['総収益'], y=[new_sum], marker_color='#3498db')
            ])
            fig_bar.update_layout(barmode='group', height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

        # --- 詳細データ ---
        st.subheader("📋 分析結果データ (上位100件)")
        # 上昇率が高い順に並び替えて、リスクのある顧客を見やすく
        st.dataframe(df_target.sort_values('上昇率', ascending=False).head(100), use_container_width=True)
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")

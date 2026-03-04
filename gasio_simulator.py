import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import json
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; overflow-wrap: break-word; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }

    [data-testid="stDataEditor"] div[data-testid="stTable"] td[aria-readonly="false"] {
        border-right: 5px solid #fdd835 !important;
        background-color: #fffde7 !important;
    }
    /* ガイダンス用スタイル */
    .import-guide { background-color: #f1f5f9; border-left: 4px solid #3498db; padding: 10px; margin-bottom: 20px; font-size: 0.85rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> シミュレーター</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">料金改定シミュレーション</div>', unsafe_allow_html=True)

# --- 共通定数 ---
CHIC_PIE_COLORS = ['#34495e', '#5dade2', '#aed6f1', '#d6eaf8', '#ebf5fb']

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def get_tier_name(usage, m_df):
    for i, r in m_df.iterrows():
        if r['MIN'] <= usage <= r['MAX']:
            return f"{r['MIN']}~{r['MAX']}"
    return "その他"

def calc_bill(usage, base, tiers_list):
    if usage == 0: return base
    for t in tiers_list:
        if t['min'] <= usage <= t['max']:
            return base + (usage * t['price'])
    return base + (usage * tiers_list[-1]['price'])

# ---------------------------------------------------------
# 3. サイドバー: データ読み込み & インポートガイダンス
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Input")
    
    # 指示2: インポートガイダンス (data_managerの構成を反映)
    st.markdown("""
    <div class="import-guide">
        <strong>💡 インポート形式</strong><br>
        1. 料金表マスター<br>
        [料金表番号, MIN, MAX, 基本料金, 単価]<br>
        2. 使用量CSV<br>
        [料金表番号, 使用量, 調定数]
    </div>
    """, unsafe_allow_html=True)

    file_m = st.file_uploader("1. 料金表マスター(CSV)", type="csv", key="m_up")
    file_u = st.file_uploader("2. 請求データ(CSV)", type="csv", key="u_up")
    
    st.divider()
    st.header("⚙️ Simulation Settings")
    sel_p = st.selectbox("対象新料金案", ["Plan-A", "Plan-B", "Plan-C"])
    
    # ユーザー入力
    new_base = st.number_input(f"{sel_p}: 基本料金", value=1500, step=100)
    num_tiers = st.slider(f"{sel_p}: 区画数", 1, 5, 3)
    
    new_tiers_list = []
    for i in range(num_tiers):
        st.markdown(f"**区画 {i+1}**")
        c1, c2 = st.columns(2)
        l_val = c1.number_input(f"上限(m3)", value=10.0*(i+1) if i<num_tiers-1 else 999.0, key=f"l_{i}")
        p_val = c2.number_input(f"単価(円)", value=600-(i*50), key=f"p_{i}")
        new_tiers_list.append({"min": 0 if i==0 else new_tiers_list[i-1]['max']+0.1, "max": l_val, "price": p_val})

    # 指示3: 「設定の復元(JSON)」および「設定の保存」ボタンを廃止

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if file_m and file_u:
    df_master_all = pd.read_csv(file_m)
    df_usage_raw = pd.read_csv(file_u)

    # 指示1: 不要なカラムを排除 (調定数は維持、取り付け数等は除外)
    needed_cols = ['料金表番号', '使用量', '調定数']
    df_usage_all = df_usage_raw[[c for c in needed_cols if c in df_usage_raw.columns]].copy()

    # フィルタリング: 対象の料金表番号を選択
    all_ids = sorted(df_master_all['料金表番号'].unique().astype(str))
    selected_ids = st.multiselect("分析対象の料金表番号", all_ids, default=all_ids[:1])
    
    if selected_ids:
        df_target_usage = df_usage_all[df_usage_all['料金表番号'].astype(str).isin(selected_ids)].copy()
        
        # --- 計算 ---
        def get_current(row):
            m = df_master_all[df_master_all['料金表番号'].astype(str) == str(row['料金表番号'])].sort_values('MIN')
            for _, r in m.iterrows():
                if r['MIN'] <= row['使用量'] <= r['MAX']:
                    return (r['基本料金'] + (row['使用量'] * r['単価'])) * row['調定数']
            return 0

        df_target_usage['現行料金'] = df_target_usage.apply(get_current, axis=1)
        df_target_usage['新料金'] = df_target_usage.apply(lambda x: calc_bill(x['使用量'], new_base, new_tiers_list) * x['調定数'], axis=1)
        df_target_usage['差額'] = df_target_usage['新料金'] - df_target_usage['現行料金']

        # --- 指標 ---
        cur_sum = df_target_usage['現行料金'].sum()
        new_sum = df_target_usage['新料金'].sum()
        
        st.markdown("### 📈 収益インパクト")
        m1, m2, m3 = st.columns(3)
        m1.metric("現行 収益総計", f"¥{cur_sum:,.0f}")
        m2.metric(f"{sel_p} 収益総計", f"¥{new_sum:,.0f}", f"{new_sum-cur_sum:+,.0f}")
        m3.metric("増減率", f"{(new_sum/cur_sum-1)*100:+.2f}%" if cur_sum > 0 else "0%")

        # --- 分布図 ---
        st.divider()
        g1, g2 = st.columns(2)
        
        # 区画の一致確認
        ids_consistent = len(df_master_all[df_master_all['料金表番号'].astype(str).isin(selected_ids)]['MIN'].unique()) <= num_tiers
        
        with g1:
            st.markdown("**Current: 現行構成**")
            if ids_consistent:
                m_rep = df_master_all[df_master_all['料金表番号'].astype(str) == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
                df_target_usage['現行区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, m_rep))
                agg_c = df_target_usage.groupby('現行区画').agg(件数=('調定数','sum'), 使用量=('使用量','sum')).reset_index()
                st.plotly_chart(px.pie(agg_c, values='件数', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
                st.dataframe(agg_c.style.format({"使用量":"{:,.1f}"}), hide_index=True, use_container_width=True)
            else:
                st.info("⚠️ 異なる区画の料金表が混在しているため、分布図を表示")
                st.plotly_chart(px.histogram(df_target_usage, x="使用量", color="料金表番号", nbins=50, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
                
        with g2:
            st.markdown(f"**Proposal: {sel_p}構成**")
            # 新区画ラベル
            def get_new_tier_label(u):
                for t in new_tiers_list:
                    if t['min'] <= u <= t['max']: return f"{t['min']}~{t['max']}"
                return "その他"
            df_target_usage['新区画'] = df_target_usage['使用量'].apply(get_new_tier_label)
            agg_n = df_target_usage.groupby('新区画').agg(件数=('調定数','sum'), 使用量=('使用量','sum')).reset_index()
            st.plotly_chart(px.pie(agg_n, values='件数', names='新区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
            st.dataframe(agg_n.style.format({"使用量":"{:,.1f}"}), hide_index=True, use_container_width=True)

        st.subheader("📋 詳細データ (上位100件)")
        st.dataframe(df_target_usage.head(100), use_container_width=True)
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")

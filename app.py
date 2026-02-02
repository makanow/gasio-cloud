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
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #fdfdfd; padding: 15px 20px; border-radius: 6px; border-left: 5px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 計算機</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Unified Simulation & Analysis</div>', unsafe_allow_html=True)

# --- カラーパレット ---
CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '上限': 'MAX', '適用上限': 'MAX', 'ID': '料金表番号',
        '単位': '単位料金', '単価': '単位料金', 'Usage': '使用量', '調定': '調定数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    # 数値化強制
    for col in ['使用量', 'MAX', '調定数']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0 if col != 'MAX' else 999999999.0)
    return df

def get_tier_label(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    df = tariff_df.copy()
    df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    sorted_df = df.sort_values('MAX').reset_index(drop=True)
    applicable = sorted_df[sorted_df['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_df.iloc[-1]
    
    if '区画名' in row and pd.notna(row['区画名']): return str(row['区画名'])
    if '区画' in row and pd.notna(row['区画']): return str(row['区画'])
    return f"Tier {row.name + 1}"

# ---------------------------------------------------------
# 3. メイン
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'], key="u_key")
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'], key="m_key")

if file_usage and file_master:
    # データ読み込み
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file_usage.seek(0); df_usage = normalize_columns(pd.read_csv(file_usage, encoding=enc))
            file_master.seek(0); df_master = normalize_columns(pd.read_csv(file_master, encoding=enc))
            break
        except: continue
    
    u_ids = sorted(df_usage['料金表番号'].unique())
    selected_ids = st.sidebar.multiselect("分析対象ID", u_ids, default=u_ids[:1])

    if selected_ids:
        # 構造整合性チェック
        fps = {}
        for tid in selected_ids:
            m_sub = df_master[df_master['料金表番号'] == tid].sort_values('MAX')
            if not m_sub.empty:
                f = sorted(m_sub['MAX'].unique())
                if f: f[-1] = 999999999.0
                fps[tid] = tuple(f)
        
        if len(set(fps.values())) > 1:
            st.error("⚠️ 選択したID間で境界線が不一致です。")
            st.stop()

        # Tab定義
        tab_design, tab_sim, tab_analysis = st.tabs(["Design", "Simulation", "Analysis"])

        # 代表マスタ (統合表示用)
        master_rep = df_master[df_master['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
        df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()

        with tab_analysis:
            st.markdown("##### 統合需要構成分析")
            
            # 【ここが修正の核心】
            # IDが複数でも、境界が同じなら問答無用で合算集計を行う
            df_target_usage['Label'] = df_target_usage['使用量'].apply(lambda x: get_tier_label(x, master_rep))
            
            agg_df = df_target_usage.groupby('Label').agg(
                調定数=('調定数', 'sum'),
                総使用量=('使用量', 'sum')
            ).reset_index()

            # 並び順を境界値の順に
            ordered_labels = [get_tier_label(r['MAX']-1e-6, master_rep) for _, r in master_rep.iterrows()]
            agg_df['order'] = agg_df['Label'].apply(lambda x: ordered_labels.index(x) if x in ordered_labels else 99)
            agg_df = agg_df.sort_values('order').drop(columns='order')

            # 表示
            total_count = agg_df['調定数'].sum()
            total_vol = agg_df['総使用量'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("合計調定数", f"{total_count:,.0f}")
            m2.metric("合計使用量", f"{total_vol:,.0f} m³")
            if total_count > 0: m3.metric("平均使用量", f"{total_vol/total_count:.1f} m³")

            g1, g2 = st.columns(2)
            with g1:
                fig1 = px.pie(agg_df, values='調定数', names='Label', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="調定数シェア")
                st.plotly_chart(fig1, use_container_width=True, key="ana_pie_1")
            with g2:
                fig2 = px.pie(agg_df, values='総使用量', names='Label', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="使用量シェア")
                st.plotly_chart(fig2, use_container_width=True, key="ana_pie_2")

            agg_df['調定数構成比'] = (agg_df['調定数'] / total_count * 100).map('{:.1f}%'.format)
            agg_df['使用量構成比'] = (agg_df['総使用量'] / (total_vol if total_vol > 0 else 1) * 100).map('{:.1f}%'.format)
            st.dataframe(agg_df[['Label', '調定数', '調定数構成比', '総使用量', '使用量構成比']], hide_index=True, use_container_width=True)

else:
    st.info("👈 サイドバーからCSVを読み込んでください。")

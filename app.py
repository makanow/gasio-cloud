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
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; text-align: left; margin-bottom: 0; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; text-align: left; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #f8f9fa; border-radius: 5px; padding: 10px; border-left: 4px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 計算機</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Cloud Edition - Robust Multi-Analysis</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX', 'max': 'MAX',
        'ID': '料金表番号', 'Code': '料金表番号',
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量',
        '調定': '調定数', 'BillingCount': '調定数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' in df.columns:
        df['料金表番号'] = pd.to_numeric(df['料金表番号'], errors='coerce').fillna(0).astype(int)
    if '使用量' in df.columns:
        df['使用量'] = pd.to_numeric(df['使用量'], errors='coerce').fillna(0.0)
    if 'MAX' in df.columns:
        df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    if '調定数' not in df.columns: df['調定数'] = 1
    return df

def smart_load(file):
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

def get_tier_label(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    # MAXでソート（適用上限(m3)が含まれる場合に対応）
    df_calc = tariff_df.copy()
    if '適用上限(m3)' in df_calc.columns:
        df_calc = df_calc.rename(columns={'適用上限(m3)': 'MAX'})
    
    df_calc['MAX'] = pd.to_numeric(df_calc['MAX'], errors='coerce').fillna(999999999.0)
    sorted_df = df_calc.sort_values('MAX').reset_index(drop=True)
    
    applicable = sorted_df[sorted_df['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_df.iloc[-1]
    
    if '区画名' in row and pd.notna(row['区画名']): return str(row['区画名'])
    rank = row.name + 1
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return letters[rank-1] if rank <= len(letters) else f"Tier{rank}"

# ---------------------------------------------------------
# 3. メイン
# ---------------------------------------------------------
if 'plan_data' not in st.session_state:
    st.session_state.plan_data = pd.DataFrame({
        'No': [1, 2, 3], '区画名': ['A', 'B', 'C'],
        '適用上限(m3)': [8.0, 30.0, 99999.0], '単位料金': [500.0, 400.0, 300.0]
    })

with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'])
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'])

if file_usage and file_master:
    df_usage = smart_load(file_usage)
    df_master = smart_load(file_master)
    
    if df_usage is not None and df_master is not None:
        u_ids = sorted(df_usage['料金表番号'].unique())
        selected_ids = st.sidebar.multiselect("対象IDを選択", u_ids, default=u_ids[:1])

        if selected_ids:
            # 境界一致チェック (指紋判定)
            fps = {}
            for tid in selected_ids:
                m_sub = df_master[df_master['料金表番号'] == tid].sort_values('MAX')
                if not m_sub.empty:
                    f = sorted(m_sub['MAX'].unique()); f[-1] = 999999999.0
                    fps[tid] = tuple(f)
            
            tab1, tab2, tab3 = st.tabs(["Design", "Simulation", "Analysis"])

            with tab3:
                st.markdown("##### 統合需要構成分析")
                if len(set(fps.values())) > 1:
                    st.warning("⚠️ 境界が異なるため合算できません。個別に選択してください。")
                else:
                    # 合算分析実行
                    df_target = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
                    master_rep = df_master[df_master['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
                    
                    df_target['Label'] = df_target['使用量'].apply(lambda x: get_tier_label(x, master_rep))
                    
                    agg_df = df_target.groupby('Label').agg(調定数=('調定数','sum'), 総使用量=('使用量','sum')).reset_index()
                    
                    # ソート順
                    ordered_labels = [get_tier_label(r['MAX']-1e-6, master_rep) for _, r in master_rep.iterrows()]
                    agg_df['order'] = agg_df['Label'].apply(lambda x: ordered_labels.index(x) if x in ordered_labels else 99)
                    agg_df = agg_df.sort_values('order').drop(columns='order')
                    
                    # 表示
                    total_c = agg_df['調定数'].sum()
                    total_v = agg_df['総使用量'].sum()
                    
                    c1, c2 = st.columns(2)
                    chic_colors = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
                    c1.plotly_chart(px.pie(agg_df, values='調定数', names='Label', hole=0.5, color_discrete_sequence=chic_colors, title="調定数シェア"), use_container_width=True)
                    c2.plotly_chart(px.pie(agg_df, values='総使用量', names='Label', hole=0.5, color_discrete_sequence=chic_colors, title="使用量シェア"), use_container_width=True)
                    
                    st.dataframe(agg_df.style.format({"調定数":"{:,.0f}", "総使用量":"{:,.1f}"}), use_container_width=True, hide_index=True)

else:
    st.info("👈 CSVを読み込んでください。")

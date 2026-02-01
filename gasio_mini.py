import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio mini", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; text-align: left; margin-bottom: 0; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; text-align: left; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #f8f9fa; border-radius: 5px; padding: 10px; border-left: 4px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Gasio mini</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Tariff Consistent Visualizer</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX', 'max': 'MAX',
        '下限': 'MIN', '適用下限': 'MIN', 'min': 'MIN',
        'ID': '料金表番号', 'Code': '料金表番号', 'code': '料金表番号',
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量',
        '調定': '調定数', 'BillingCount': '調定数', '取付': '取付数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
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

# 【修正】ラベルを境界値ベースで生成し、表示を統一
def get_standard_tier_label(usage, sorted_master):
    if sorted_master.empty: return "Unknown"
    applicable = sorted_master[sorted_master['MAX'] >= usage]
    if applicable.empty:
        row = sorted_master.iloc[-1]
    else:
        row = applicable.iloc[0]
    
    # 境界値を見出しにする (例: "0 - 20 m³")
    min_val = row['MIN'] if 'MIN' in row else 0
    return f"{min_val:g} - {row['MAX']:g} m³"

# ---------------------------------------------------------
# 3. サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'])
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'])

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if file_usage and file_master:
    df_usage = smart_load(file_usage)
    df_master = smart_load(file_master)
    
    if df_usage is None or df_master is None:
        st.error("データの読み込みに失敗しました。")
        st.stop()

    usage_ids = sorted(df_usage['料金表番号'].unique())
    selected_ids = st.multiselect("分析対象の料金表番号を選択", usage_ids, default=usage_ids[:1])

    if not selected_ids:
        st.stop()

    # --- 構造チェック ---
    structures = {}
    for tid in selected_ids:
        m_sub = df_master[df_master['料金表番号'] == tid]
        if m_sub.empty: continue
        # MAX値を指紋にする
        fingerprint = tuple(sorted(m_sub['MAX'].unique()))
        structures[tid] = fingerprint

    unique_patterns = set(structures.values())

    if len(unique_patterns) > 1:
        st.error("⚠️ 選択された料金表間で区画の境界線が異なります。")
        for tid, fp in structures.items():
            st.write(f"ID {tid}: 境界 {list(fp)}")
        st.stop()

    # --- 判定と集計 ---
    df_target = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    master_rep = df_master[df_master['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)

    # ラベル生成
    df_target['Current_Tier'] = df_target['使用量'].apply(lambda x: get_standard_tier_label(x, master_rep))

    # 集計 (Current_Tier の並び順を MAX 値に合わせるためマスタと紐付け)
    agg_df = df_target.groupby('Current_Tier').agg(
        調定数=('調定数', 'sum'),
        総使用量=('使用量', 'sum')
    ).reset_index()

    # ソート順を正しくするためのマッピング
    tier_order = {get_standard_tier_label(r['MAX']-0.001, master_rep): i for i, r in master_rep.iterrows()}
    agg_df['order'] = agg_df['Current_Tier'].map(tier_order)
    agg_df = agg_df.sort_values('order').drop(columns=['order'])

    # --- ビジュアル ---
    st.markdown("---")
    total_count = agg_df['調定数'].sum()
    total_vol = agg_df['総使用量'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("合計調定数", f"{total_count:,}")
    m2.metric("合計使用量", f"{total_vol:,.0f} m³")
    if total_count > 0: m3.metric("1件あたり平均", f"{total_vol/total_count:.1f} m³")

    chic_colors = ['#88a0b9', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f', '#aab7b8']
    g1, g2 = st.columns(2)
    with g1:
        st.write("**調定数シェア**")
        fig1 = px.pie(agg_df, values='調定数', names='Current_Tier', hole=0.5, color_discrete_sequence=chic_colors, sort=False)
        st.plotly_chart(fig1, use_container_width=True)
    with g2:
        st.write("**使用量シェア**")
        fig2 = px.pie(agg_df, values='総使用量', names='Current_Tier', hole=0.5, color_discrete_sequence=chic_colors, sort=False)
        st.plotly_chart(fig2, use_container_width=True)

    agg_df['調定数構成比'] = (agg_df['調定数'] / total_count * 100).map('{:.1f}%'.format)
    agg_df['使用量構成比'] = (agg_df['総使用量'] / total_vol * 100).map('{:.1f}%'.format)
    st.dataframe(agg_df[['Current_Tier', '調定数', '調定数構成比', '総使用量', '使用量構成比']], hide_index=True, use_container_width=True)

else:
    st.info("👈 CSVをアップロードしてください。")

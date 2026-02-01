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
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; text-align: left; margin-bottom: 0; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; text-align: left; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #f8f9fa; border-radius: 5px; padding: 10px; border-left: 4px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> mini</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Current Status Visualizer (Consistent Structure Mode)</div>', unsafe_allow_html=True)

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
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量', 'Volume': '使用量',
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

def get_tier_name(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    sorted_df = tariff_df.sort_values('MAX').reset_index(drop=True)
    # 浮動小数点の誤差を考慮し微小値を加算
    applicable = sorted_df[sorted_df['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_df.iloc[-1]
    
    if '区画名' in row and pd.notna(row['区画名']): return str(row['区画名'])
    rank = row.name + 1
    return f"Tier {rank}"

# ---------------------------------------------------------
# 3. メイン処理
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV (実績)", type=['csv'])
    file_master = st.file_uploader("2. 料金表マスタCSV (定義)", type=['csv'])

if file_usage and file_master:
    df_usage = smart_load(file_usage)
    df_master = smart_load(file_master)
    
    if df_usage is not None and df_master is not None:
        usage_ids = sorted(df_usage['料金表番号'].unique())
        
        # Q: どの料金表を合算するか？ (マルチセレクトに変更)
        selected_ids = st.multiselect("分析対象の料金表番号を選択 (複数選択で合算判定を行います)", usage_ids, default=usage_ids[:1])
        
        if not selected_ids:
            st.info("分析するIDを選択してください。")
            st.stop()

        # --- 構造一致チェック ---
        # 各IDのMAX値のセットを比較する
        structure_check = {}
        for tid in selected_ids:
            m_sub = df_master[df_master['料金表番号'] == tid]
            if not m_sub.empty:
                # MAX値をソートしたタプルを「構造の指紋」とする
                fingerprint = tuple(sorted(m_sub['MAX'].unique()))
                structure_check[tid] = fingerprint
        
        unique_structures = set(structure_check.values())
        
        if len(unique_structures) > 1:
            st.error("⚠️ 選択された料金表間で「区画の境界(MAX値)」が一致しません。合算分析は不可能です。")
            st.write("各IDの境界設定:", structure_check)
            st.stop()
        
        # --- 分析実行 ---
        df_target = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
        # 代表として最初のIDのマスタを使用
        master_rep = df_master[df_master['料金表番号'] == selected_ids[0]].copy()
        
        df_target['Current_Tier'] = df_target['使用量'].apply(lambda x: get_tier_name(x, master_rep))
        
        agg_df = df_target.groupby('Current_Tier').agg(
            調定数=('調定数', 'sum'),
            総使用量=('使用量', 'sum')
        ).reset_index().sort_values('Current_Tier')

        # 可視化
        st.markdown("---")
        total_count = agg_df['調定数'].sum()
        total_vol = agg_df['総使用量'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("合計調定数", f"{total_count:,}")
        m2.metric("合計使用量", f"{total_vol:,.0f} m³")
        if total_count > 0:
            m3.metric("1件あたり平均", f"{total_vol/total_count:.1f} m³")

        chic_colors = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
        g1, g2 = st.columns(2)
        
        # グラフ描画
        with g1:
            st.markdown("**調定数シェア**")
            fig1 = px.pie(agg_df, values='調定数', names='Current_Tier', hole=0.5, color_discrete_sequence=chic_colors)
            fig1.update_traces(textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
            
        with g2:
            st.markdown("**使用量シェア**")
            fig2 = px.pie(agg_df, values='総使用量', names='Current_Tier', hole=0.5, color_discrete_sequence=chic_colors)
            fig2.update_traces(textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)

        # 構成比計算
        if total_count > 0:
            agg_df['調定数構成比'] = (agg_df['調定数'] / total_count * 100).map('{:.1f}%'.format)
        if total_vol > 0:
            agg_df['使用量構成比'] = (agg_df['総使用量'] / total_vol * 100).map('{:.1f}%'.format)
        
        st.markdown("**詳細データ**")
        st.dataframe(agg_df[['Current_Tier', '調定数', '調定数構成比', '総使用量', '使用量構成比']], hide_index=True, use_container_width=True)
else:
    st.info("👈 サイドバーからCSVをアップロードしてください。")

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
st.markdown('<div class="sub-title">Current Status Visualizer</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '下限': 'MIN', 'ID': '料金表番号',
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量',
        '調定': '調定数', '取付': '取付数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    # 数値変換の強制
    if '使用量' in df.columns: df['使用量'] = pd.to_numeric(df['使用量'], errors='coerce').fillna(0)
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
    # ここで変数名を sorted_df に統一（修正ポイント）
    sorted_df = tariff_df.sort_values('MAX').reset_index(drop=True)
    applicable = sorted_df[sorted_df['MAX'] >= usage]
    
    if applicable.empty:
        row = sorted_df.iloc[-1]
    else:
        row = applicable.iloc[0]
    
    if '区画名' in row and pd.notna(row['区画名']): return str(row['区画名'])
    rank = row.name + 1
    return f"Tier {rank}"

# ---------------------------------------------------------
# 3. メイン
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'])
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'])

if file_usage and file_master:
    df_usage = smart_load(file_usage)
    df_master = smart_load(file_master)
    
    if df_usage is not None and df_master is not None:
        usage_ids = sorted(df_usage['料金表番号'].unique())
        
        # 最初は確実に動く「単一選択」
        target_id = st.selectbox("分析する料金表番号を選択", usage_ids)
        
        df_target = df_usage[df_usage['料金表番号'] == target_id].copy()
        master_target = df_master[df_master['料金表番号'] == target_id].copy()
        
        if not df_target.empty and not master_target.empty:
            # 判定
            df_target['Current_Tier'] = df_target['使用量'].apply(lambda x: get_tier_name(x, master_target))
            
            # 集計
            agg_df = df_target.groupby('Current_Tier').agg({
                '調定数': 'sum',
                '使用量': 'sum'
            }).reset_index()
            
            st.write(f"### 📊 ID: {target_id} の集計結果")
            st.dataframe(agg_df, use_container_width=True)
            
            # グラフ表示（簡易版）
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.pie(agg_df, values='調定数', names='Current_Tier', title="調定数シェア"), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(agg_df, values='使用量', names='Current_Tier', title="使用量シェア"), use_container_width=True)
        else:
            st.warning("対象データの抽出に失敗しました。")
else:
    st.info("👈 CSVをアップロードしてください。")

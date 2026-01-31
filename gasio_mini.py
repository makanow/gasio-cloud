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
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2c3e50; text-align: center; margin-bottom: 0; }
    .sub-title { font-size: 1.0rem; color: #7f8c8d; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #f8f9fa; border-radius: 5px; padding: 10px; border-left: 4px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> mini</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Current Status Visualizer</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義 (強化版)
# ---------------------------------------------------------
def normalize_columns(df):
    # 徹底的に揺らぎを吸収するマップ
    rename_map = {
        # 料金マスタ系
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金', 'base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金', 'Unit': '単位料金', 'unit': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX', 'max': 'MAX',
        '下限': 'MIN', '適用下限': 'MIN', 'min': 'MIN',
        'ID': '料金表番号', 'Code': '料金表番号', 'code': '料金表番号',
        # 使用量系 (ここを強化)
        'Usage': '使用量', 'usage': '使用量',
        'Vol': '使用量', 'vol': '使用量', 'Volume': '使用量', 'volume': '使用量',
        'Amount': '使用量', 'amount': '使用量',
        'm3': '使用量', '㎥': '使用量',
        # その他
        '調定': '調定数', 'BillingCount': '調定数', 'Billable': '調定数',
        '取付': '取付数', 'MeterCount': '取付数'
    }
    df = df.rename(columns=rename_map)
    
    # 必須カラム補完
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    return df

def smart_load(file):
    file.seek(0)
    # 読み込み試行
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            # カラム名の空白除去
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

def get_tier_name(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    sorted_df = tariff_df.sort_values('MAX').reset_index(drop=True)
    applicable = sorted_df[sorted_df['MAX'] >= usage]
    if applicable.empty:
        row = sorted_df.iloc[-1]
    else:
        row = applicable.iloc[0]
    
    if '区画名' in row and pd.notna(row['区画名']): return str(row['区画名'])
    if '区画' in row and pd.notna(row['区画']): return str(row['区画'])
    
    rank = row.name + 1
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    label = letters[rank-1] if rank <= len(letters) else f"Tier{rank}"
    return label

# ---------------------------------------------------------
# 3. サイドバー (ファイルアップロード)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV (実績)", type=['csv'])
    file_master = st.file_uploader("2. 料金マスタCSV (定義)", type=['csv'])
    st.info("💡 CSVヘッダーに「使用量」または「Usage」を含めてください。")

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if file_usage and file_master:
    # データ読み込み
    df_usage = smart_load(file_usage)
    df_master = smart_load(file_master)
    
    # エラーハンドリング強化
    if df_usage is None or df_master is None:
        st.error("データの読み込みに失敗しました。")
        st.stop()
        
    # カラム存在チェック
    if '使用量' not in df_usage.columns:
        st.error(f"❌ 使用量データに『使用量』列が見つかりません。\n\n検出された列名: {list(df_usage.columns)}")
        st.stop()

    # マスタにある料金表番号リスト
    master_ids = sorted(df_master['料金表番号'].unique())
    usage_ids = sorted(df_usage['料金表番号'].unique())
    valid_ids = [i for i in master_ids if i in usage_ids]
    
    if not valid_ids:
        st.warning(f"マスタと使用量データで一致する「料金表番号」がありません。\nマスタ側ID: {master_ids}\n使用量側ID: {usage_ids}")
        st.stop()
        
    # --- 分析開始 ---
    st.write(f"✅ 分析対象データ: {len(df_usage):,} 件 (ID数: {len(valid_ids)})")
    col_sel, _ = st.columns([1, 2])
    target_id = col_sel.selectbox("分析する料金表番号を選択", valid_ids)
    
    # データ抽出
    df_target = df_usage[df_usage['料金表番号'] == target_id].copy()
    master_target = df_master[df_master['料金表番号'] == target_id].copy()
    
    if df_target.empty:
        st.warning("選択されたIDのデータがありません。")
        st.stop()

    # マスタ確認
    with st.expander("マスタ定義 (区画情報) を確認"):
        cols = [c for c in ['区画','区画名','MIN','MAX','基本料金','単位料金'] if c in master_target.columns]
        st.dataframe(master_target[cols], hide_index=True)

    # 区画判定
    try:
        df_target['Current_Tier'] = df_target['使用量'].apply(lambda x: get_tier_name(x, master_target))
    except Exception as e:
        st.error(f"区画判定中にエラーが発生しました: {e}")
        st.stop()
    
    # 集計
    agg_df = df_target.groupby('Current_Tier').agg(
        調定数=('調定数', 'sum'),
        総使用量=('使用量', 'sum')
    ).reset_index().sort_values('Current_Tier')

    # 可視化
    st.markdown("---")
    st.markdown(f"### 📊 料金表: {target_id} の構成分析")
    
    total_count = agg_df['調定数'].sum()
    total_vol = agg_df['総使用量'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("合計調定数", f"{total_count:,}")
    c2.metric("合計使用量", f"{total_vol:,.0f} m³")
    if total_count > 0:
        c3.metric("1件あたり平均", f"{total_vol/total_count:.1f} m³")

    chic_colors = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
    g1, g2 = st.columns(2)
    
    with g1:
        st.markdown("**調定数シェア**")
        fig_count = px.pie(agg_df, values='調定数', names='Current_Tier', hole=0.5, color_discrete_sequence=chic_colors)
        fig_count.update_traces(textinfo='percent+label', textposition='inside')
        st.plotly_chart(fig_count, use_container_width=True)
        
    with g2:
        st.markdown("**使用量シェア**")
        fig_vol = px.pie(agg_df, values='総使用量', names='Current_Tier', hole=0.5, color_discrete_sequence=chic_colors)
        fig_vol.update_traces(textinfo='percent+label', textposition='inside')
        st.plotly_chart(fig_vol, use_container_width=True)

    agg_df['調定数構成比'] = (agg_df['調定数'] / total_count * 100).map('{:.1f}%'.format)
    agg_df['使用量構成比'] = (agg_df['総使用量'] / total_vol * 100).map('{:.1f}%'.format)
    
    st.markdown("**詳細データ**")
    st.dataframe(agg_df[['Current_Tier', '調定数', '調定数構成比', '総使用量', '使用量構成比']], hide_index=True, use_container_width=True)

else:
    st.info("👈 サイドバーから「使用量CSV」と「料金マスタCSV」をアップロードしてください。")
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
# 2. 関数定義 (Gasio Core Logic移植)
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX',
        '下限': 'MIN', '適用下限': 'MIN',
        'ID': '料金表番号', 'Code': '料金表番号',
        '調定': '調定数', 'BillingCount': '調定数', 'Billable': '調定数',
        '取付': '取付数', 'MeterCount': '取付数'
    }
    df = df.rename(columns=rename_map)
    # 必須カラム補完
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    return df

def smart_load(file):
    # レートメイク形式等は簡易対応（CSV読み込みトライ）
    file.seek(0)
    for enc in ['cp932', 'utf-8', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

def get_tier_name(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    # MAXでソート
    sorted_df = tariff_df.sort_values('MAX').reset_index(drop=True)
    # 該当行を探す
    applicable = sorted_df[sorted_df['MAX'] >= usage]
    if applicable.empty:
        row = sorted_df.iloc[-1] # 上限超えは最後の行
    else:
        row = applicable.iloc[0]
    
    # 区画名を取得
    if '区画名' in row and pd.notna(row['区画名']): return str(row['区画名'])
    if '区画' in row and pd.notna(row['区画']): return str(row['区画'])
    
    # なければ自動命名
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
    
    st.info("💡 Gasio計算機と同じCSVが使えます。")

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if file_usage and file_master:
    # データ読み込み
    df_usage = smart_load(file_usage)
    df_master = smart_load(file_master)
    
    if df_usage is None or df_master is None:
        st.error("データの読み込みに失敗しました。フォーマットを確認してください。")
        st.stop()
        
    # マスタにある料金表番号リスト
    master_ids = sorted(df_master['料金表番号'].unique())
    usage_ids = sorted(df_usage['料金表番号'].unique())
    
    # 共通するIDのみ抽出
    valid_ids = [i for i in master_ids if i in usage_ids]
    
    if not valid_ids:
        st.warning("マスタと使用量データで一致する「料金表番号」がありません。")
        st.stop()
        
    # --- セレクター ---
    st.write(f"✅ 分析対象データ: {len(df_usage):,} 件 (ID数: {len(valid_ids)})")
    
    col_sel, _ = st.columns([1, 2])
    target_id = col_sel.selectbox("分析する料金表番号を選択", valid_ids)
    
    # --- フィルタリング & 分析 ---
    # 1. 対象データの抽出
    df_target = df_usage[df_usage['料金表番号'] == target_id].copy()
    master_target = df_master[df_master['料金表番号'] == target_id].copy()
    
    if df_target.empty or master_target.empty:
        st.warning("データが存在しません。")
        st.stop()

    # 2. マスタ情報の表示 (Expander)
    with st.expander("マスタ定義 (区画情報) を確認"):
        cols = [c for c in ['区画','区画名','MIN','MAX','基本料金','単位料金'] if c in master_target.columns]
        st.dataframe(master_target[cols], hide_index=True)

    # 3. 区画判定 (Gasio Logic)
    # ここで計算機と同じロジックで「どの区画か？」を判定する
    df_target['Current_Tier'] = df_target['使用量'].apply(lambda x: get_tier_name(x, master_target))
    
    # 4. 集計 (Aggregation)
    # 調定数ベースでの集計（調定数0の行は構成比には含めない等の処理が必要ならここでフィルタ）
    # Gasio計算機同様、sumをとる
    agg_df = df_target.groupby('Current_Tier').agg(
        調定数=('調定数', 'sum'),
        総使用量=('使用量', 'sum')
    ).reset_index()
    
    # マスタの区画順に並べ替えたい（アルファベット順などで簡易ソート）
    agg_df = agg_df.sort_values('Current_Tier')

    # 5. 可視化 (Visualization)
    st.markdown("---")
    st.markdown(f"### 📊 料金表: {target_id} の構成分析")
    
    # KPI
    total_count = agg_df['調定数'].sum()
    total_vol = agg_df['総使用量'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("合計調定数", f"{total_count:,}")
    c2.metric("合計使用量", f"{total_vol:,.0f} m³")
    if total_count > 0:
        c3.metric("1件あたり平均", f"{total_vol/total_count:.1f} m³")

    # 円グラフ
    g1, g2 = st.columns(2)
    
    # パレット
    chic_colors = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
    
    with g1:
        st.markdown("**調定数シェア (Count %)**")
        fig_count = px.pie(agg_df, values='調定数', names='Current_Tier', 
                          hole=0.5, color_discrete_sequence=chic_colors)
        fig_count.update_traces(textinfo='percent+label', textposition='inside')
        st.plotly_chart(fig_count, use_container_width=True)
        
    with g2:
        st.markdown("**使用量シェア (Volume %)**")
        fig_vol = px.pie(agg_df, values='総使用量', names='Current_Tier', 
                        hole=0.5, color_discrete_sequence=chic_colors)
        fig_vol.update_traces(textinfo='percent+label', textposition='inside')
        st.plotly_chart(fig_vol, use_container_width=True)

    # 集計表
    st.markdown("**詳細データ**")
    # シェア(%)を計算して表示
    agg_df['調定数構成比'] = (agg_df['調定数'] / total_count * 100).map('{:.1f}%'.format)
    agg_df['使用量構成比'] = (agg_df['総使用量'] / total_vol * 100).map('{:.1f}%'.format)
    
    st.dataframe(
        agg_df[['Current_Tier', '調定数', '調定数構成比', '総使用量', '使用量構成比']].style.format({
            '調定数': '{:,}', 
            '総使用量': '{:,.1f}'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # ヒストグラム (おまけ)
    with st.expander("分布ヒストグラムを見る"):
        fig_hist = px.histogram(df_target, x="使用量", nbins=100, color="Current_Tier",
                               title="使用量分布（区画別色分け）",
                               color_discrete_sequence=chic_colors)
        st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("👈 サイドバーから「使用量CSV」と「料金マスタCSV」をアップロードしてください。")
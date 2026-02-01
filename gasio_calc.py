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
st.markdown('<div class="sub-title">Unified Usage Analyzer</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '上限': 'MAX', '下限': 'MIN', 'ID': '料金表番号',
        '適用上限': 'MAX', 'Usage': '使用量', 'Vol': '使用量', '調定': '調定数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    if '使用量' in df.columns: df['使用量'] = pd.to_numeric(df['使用量'], errors='coerce').fillna(0)
    if 'MAX' in df.columns: df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
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

def get_consistent_label(usage, master_template):
    """
    複数ID合算時でも、代表マスタの「区画名」を返す。
    """
    if master_template.empty: return "Unknown"
    # 境界判定
    applicable = master_template[master_template['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else master_template.iloc[-1]
    
    # ラベル取得（区画名 > 区画 > Tier番号）
    for col in ['区画名', '区画']:
        if col in row and pd.notna(row[col]):
            return str(row[col])
    return f"Tier {row.name + 1}"

# ---------------------------------------------------------
# 3. メイン処理
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
        selected_ids = st.multiselect("分析対象の料金表番号を選択", usage_ids, default=usage_ids[:1])

        if selected_ids:
            # 構造指紋チェック
            fps = {}
            for tid in selected_ids:
                m_sub = df_master[df_master['料金表番号'] == tid].sort_values('MAX')
                if not m_sub.empty:
                    m_fps = sorted(m_sub['MAX'].unique())
                    if m_fps: m_fps[-1] = 999999999.0 
                    fps[tid] = tuple(m_fps)
            
            if len(set(fps.values())) > 1:
                st.error("⚠️ 境界線が不一致なIDが選択されています。")
                st.stop()

            # --- 合算・分析 ---
            df_target = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
            # 代表ラベル用のマスタテンプレート
            master_rep = df_master[df_master['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
            
            # 代表ラベルを付与
            df_target['Tier_Label'] = df_target['使用量'].apply(lambda x: get_consistent_label(x, master_rep))
            
            # 集計
            agg_df = df_target.groupby('Tier_Label').agg({'調定数': 'sum', '使用量': 'sum'}).reset_index()
            
            # 並び順の制御
            ordered_labels = [get_consistent_label(r['MAX']-1e-6, master_rep) for _, r in master_rep.iterrows()]
            agg_df['order'] = agg_df['Tier_Label'].apply(lambda x: ordered_labels.index(x) if x in ordered_labels else 99)
            agg_df = agg_df.sort_values('order').drop(columns=['order'])

            # --- 表示（画像のデザインを完全再現） ---
            st.markdown("---")
            total_count = agg_df['調定数'].sum()
            total_vol = agg_df['使用量'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("合計調定数", f"{total_count:,.0f}")
            m2.metric("合計使用量", f"{total_vol:,.0f} m³")
            if total_count > 0:
                m3.metric("1件あたり平均", f"{total_vol/total_count:.1f} m³")

            chic_colors = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
            g1, g2 = st.columns(2)
            with g1:
                st.write("**調定数シェア**")
                fig1 = px.pie(agg_df, values='調定数', names='Tier_Label', hole=0.5, color_discrete_sequence=chic_colors)
                fig1.update_traces(textinfo='percent+label')
                st.plotly_chart(fig1, use_container_width=True)
            with g2:
                st.write("**使用量シェア**")
                fig2 = px.pie(agg_df, values='使用量', names='Tier_Label', hole=0.5, color_discrete_sequence=chic_colors)
                fig2.update_traces(textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)

            agg_df['調定数構成比'] = (agg_df['調定数'] / total_count * 100).map('{:.1f}%'.format)
            agg_df['使用量構成比'] = (agg_df['使用量'] / (total_vol if total_vol > 0 else 1) * 100).map('{:.1f}%'.format)
            
            st.markdown("**詳細データテーブル**")
            st.dataframe(agg_df[['Tier_Label', '調定数', '調定数構成比', '使用量', '使用量構成比']].rename(columns={'Tier_Label': '区画名', '使用量': '総使用量'}), hide_index=True, use_container_width=True)

else:
    st.info("👈 サイドバーからCSVをアップロードしてください。")

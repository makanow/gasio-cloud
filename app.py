import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import json
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Style)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gasio計算機", 
    page_icon="🔥",
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #fdfdfd; padding: 15px 20px; border-radius: 6px; border-left: 5px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 計算機</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Cloud Edition - Robust Analysis Mode</div>', unsafe_allow_html=True)

# --- カラーパレット ---
CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
COLOR_BAR = '#34495e'
COLOR_CURRENT = '#95a5a6'
COLOR_NEW = '#e67e22'

# ---------------------------------------------------------
# 2. 関数定義 (移植ロジック)
# ---------------------------------------------------------

def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX', 'max': 'MAX',
        '下限': 'MIN', '適用下限': 'MIN',
        'ID': '料金表番号', 'Code': '料金表番号',
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量',
        '調定': '調定数', 'BillingCount': '調定数', '取付': '取付数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    # 数値化ガード
    if '使用量' in df.columns: df['使用量'] = pd.to_numeric(df['使用量'], errors='coerce').fillna(0.0)
    if 'MAX' in df.columns: df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    return df

def get_fingerprint(df_m, ids):
    """Miniから移植：上限揺らぎを吸収する指紋判定"""
    check_map = {}
    for tid in ids:
        m_sub = df_m[df_m['料金表番号'] == tid].sort_values('MAX')
        if not m_sub.empty:
            fps = sorted(m_sub['MAX'].unique())
            if fps: fps[-1] = 999999999.0 # 上限固定
            check_map[tid] = tuple(fps)
    return check_map

def get_tier_name(usage, tariff_df):
    """Miniから移植：判定ラベル取得"""
    if tariff_df.empty: return "Unknown"
    # 上限揺らぎを考慮したソート
    df = tariff_df.copy()
    if 'MAX' in df.columns:
        df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    sorted_df = df.sort_values('MAX').reset_index(drop=True)
    applicable = sorted_df[sorted_df['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_df.iloc[-1]
    
    if '区画名' in row and pd.notna(row['区画名']): return str(row['区画名'])
    if '区画' in row and pd.notna(row['区画']): return str(row['区画'])
    
    rank = row.name + 1
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return letters[rank-1] if rank <= len(letters) else f"Tier{rank}"

def calculate_slide_rates(base_a, blocks_df):
    blocks = blocks_df.copy().sort_values('No')
    base_fees = {blocks.iloc[0]['No']: base_a}
    for i in range(1, len(blocks)):
        prev = blocks.iloc[i-1]
        curr = blocks.iloc[i]
        # 算式：次区画基本 = 前区画基本 + (前単価 - 現単価) * 前上限
        base_fees[curr['No']] = base_fees[prev['No']] + (prev['単位料金'] - curr['単位料金']) * prev['適用上限(m3)']
    return base_fees

def calculate_bill_single(usage, tariff_df, billing_count=1):
    if billing_count == 0 or tariff_df.empty: return 0
    # 判定用MAXを一時的に正規化
    df = tariff_df.copy()
    df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    target = df[df['MAX'] >= (usage - 1e-9)].sort_values('MAX')
    row = target.iloc[0] if not target.empty else df.sort_values('MAX').iloc[-1]
    return int(row['基本料金'] + (usage * row['単位料金']))

# ---------------------------------------------------------
# 3. サイドバー (省略なし)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'])
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'])

    selected_ids = []
    if file_master:
        # ここで読み込んで整合性チェック
        for enc in ['utf-8', 'cp932', 'shift_jis']:
            try:
                file_master.seek(0)
                df_raw = pd.read_csv(file_master, encoding=enc)
                df_master_all = normalize_columns(df_raw)
                break
            except: continue
        
        if 'df_master_all' in locals():
            u_ids = sorted(df_master_all['料金表番号'].unique())
            selected_ids = st.multiselect("対象料金表 (境界一致で合算)", u_ids, default=u_ids)
            
            if selected_ids:
                # 移植：指紋チェック
                fps = get_fingerprint(df_master_all, selected_ids)
                if len(set(fps.values())) > 1:
                    st.error("⚠️ 境界線が不一致なIDが混在しています。合算分析は不可能です。")
                    selected_ids = []
                else:
                    st.success("✅ 境界線が一致しました。合算モード有効。")

# ---------------------------------------------------------
# 4. メインエリア
# ---------------------------------------------------------
if file_usage and file_master and selected_ids:
    # データ確定
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file_usage.seek(0)
            df_usage = normalize_columns(pd.read_csv(file_usage, encoding=enc))
            break
        except: continue
    
    df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    
    # シミュレーション用タブ
    tab1, tab2, tab3 = st.tabs(["Design", "Simulation", "Analysis"])

    with tab1:
        # (Design UI は既存を継承し、内部で get_tier_name を使用するように調整)
        st.markdown("##### 料金プラン設計")
        # --- (Plan設計の中身は既存踏襲だが、最終的な res_df を get_tier_name に対応させる) ---
        # ※ ここではスペースの都合上、Tab3の移植をメインに記述
        # [既存のPlan 1-5 設計ロジックが入る]
        # 仮のプラン1を生成 (実際はUIで設定)
        if 'plan_data' not in st.session_state:
            st.session_state.plan_data = pd.DataFrame({'No':[1,2,3], '区画名':['A','B','C'], '適用上限(m3)':[8.0, 30.0, 99999.0], '単位料金':[500.0, 400.0, 300.0]})
        
        base_a = st.number_input("A区画 基本料金", value=1500.0)
        edited = st.data_editor(st.session_state.plan_data, use_container_width=True)
        bases = calculate_slide_rates(base_a, edited)
        res_list = []
        p_max = 0
        for _, r in edited.iterrows():
            res_list.append({"区画":r['区画名'], "MIN":p_max, "MAX":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']})
            p_max = r['適用上限(m3)']
        new_plan_df = pd.DataFrame(res_list)
        st.dataframe(new_plan_df)

    with tab3:
        st.markdown("##### 統合需要構成分析")
        st.info("💡 複数IDが選択されていても、境界が一致しているため合算して表示しています。")
        
        # 判定
        # 現行：代表として最初に選んだIDのマスタを使用
        master_rep = df_master_all[df_master_all['料金表番号'] == selected_ids[0]].copy()
        df_target_usage['現行区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, master_rep))
        df_target_usage['新プラン区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, new_plan_df.rename(columns={'MAX':'MAX'})))
        
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Current: 現行(合算)**")
            agg_c = df_target_usage.groupby('現行区画').agg(調定数=('調定数','sum'), 総使用量=('使用量','sum')).reset_index()
            # 並び順を境界値の順に
            labels_order = [get_tier_name(r['MAX']-1e-6, master_rep) for _, r in master_rep.sort_values('MAX').iterrows()]
            agg_c['order'] = agg_c['現行区画'].apply(lambda x: labels_order.index(x) if x in labels_order else 99)
            agg_c = agg_c.sort_values('order').drop(columns='order')
            
            c_pie1, c_pie2 = st.columns(2)
            c_pie1.plotly_chart(px.pie(agg_c, values='調定数', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="調定数"), use_container_width=True, key="c_pie1")
            c_pie2.plotly_chart(px.pie(agg_c, values='総使用量', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="使用量"), use_container_width=True, key="c_pie2")
            st.dataframe(agg_c, use_container_width=True, hide_index=True)

        with g2:
            st.markdown("**Proposal: 新プラン**")
            agg_n = df_target_usage.groupby('新プラン区画').agg(調定数=('調定数','sum'), 総使用量=('使用量','sum')).reset_index()
            # 新プランの並び順
            labels_order_n = [get_tier_name(r['MAX']-1e-6, new_plan_df) for _, r in new_plan_df.sort_values('MAX').iterrows()]
            agg_n['order'] = agg_n['新プラン区画'].apply(lambda x: labels_order_n.index(x) if x in labels_order_n else 99)
            agg_n = agg_n.sort_values('order').drop(columns='order')

            n_pie1, n_pie2 = st.columns(2)
            n_pie1.plotly_chart(px.pie(agg_n, values='調定数', names='新プラン区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="調定数"), use_container_width=True, key="n_pie1")
            n_pie2.plotly_chart(px.pie(agg_n, values='総使用量', names='新プラン区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="使用量"), use_container_width=True, key="n_pie2")
            st.dataframe(agg_n, use_container_width=True, hide_index=True)

else:
    st.info("👈 左側のサイドバーからデータを読み込んでください")

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
st.set_page_config(page_title="Gasio計算機 Pro", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

CHIC_COLORS = ["#2c3e50", "#3498db", "#e74c3c", "#f1c40f", "#2ecc71", "#9b59b6"]
CHIC_PIE_COLORS = ["#34495e", "#3498db", "#95a5a6", "#bdc3c7", "#ecf0f1"]

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">Gasio計算機 <span style="color:#3498db">Pro</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ガス料金シミュレーション・分析プラットフォーム</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数・ロジック
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {'料金表ID': '料金表番号', '料金表コード': '料金表番号', '顧客ID': '顧客番号', '月間使用量': '使用量', '当月使用量': '使用量'}
    df = df.rename(columns=rename_map)
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(r'[¥,]', '', regex=True)
            try: df[col] = pd.to_numeric(df[col])
            except: pass
    return df

def get_tier_name(usage, m_df):
    m_df = m_df.sort_values('MAX')
    for _, row in m_df.iterrows():
        if usage <= row['MAX']:
            return f"{row['MAX']}m3迄"
    return "上限超え"

def calculate_fee(usage, m_df):
    m_df = m_df.sort_values('MAX')
    for _, row in m_df.iterrows():
        if usage <= row['MAX']:
            return round(row['基本料金'] + (usage * row['従量単価']), 0)
    return 0

# 2. インポートガイダンス用のサンプルCSV生成
def get_sample_usage_csv():
    return pd.DataFrame({'料金表番号': ['A01']*3 + ['B02']*2, '使用量': [5.5, 12.0, 45.8, 8.2, 22.1]}).to_csv(index=False).encode('utf-8-sig')

def get_sample_master_csv():
    return pd.DataFrame({
        '料金表番号': ['A01', 'A01', 'B02', 'B02'], '料金表名': ['一般', '一般', 'エコ', 'エコ'],
        'MAX': [10, 99999, 20, 99999], '基本料金': [1000, 1500, 800, 1200], '従量単価': [200, 180, 220, 200]
    }).to_csv(index=False).encode('utf-8-sig')

# ---------------------------------------------------------
# 3. サイドバー: インポートガイダンス & 入力
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    
    # デモモードの選択
    demo_mode = st.toggle("デモモード（サンプルデータを使用）", value=False)
    
    # 2. CSVインポートガイダンス
    with st.expander("ℹ️ CSVインポートガイダンス", expanded=not demo_mode):
        st.markdown("""
        **【使用量CSV】**
        - `料金表番号`, `使用量`
        - ※調定数・取り付け数は不要です。
        
        **【料金表マスタCSV】**
        - `料金表番号`, `MAX`, `基本料金`, `従量単価`
        """)
        st.download_button("使用量CSVサンプル", get_sample_usage_csv(), "usage_sample.csv")
        st.download_button("マスタCSVサンプル", get_sample_master_csv(), "master_sample.csv")

    if not demo_mode:
        u_file = st.file_uploader("使用量CSV", type="csv")
        m_file = st.file_uploader("料金表マスタCSV", type="csv")
    else:
        st.info("💡 デモデータをロード中")
        u_file = io.BytesIO(get_sample_usage_csv())
        m_file = io.BytesIO(get_sample_master_csv())

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if u_file and m_file:
    df_usage = normalize_columns(pd.read_csv(u_file, encoding='utf-8-sig'))
    df_master_all = normalize_columns(pd.read_csv(m_file, encoding='utf-8-sig'))

    # 1. 調定数・取り付け数の削除
    df_usage = df_usage.drop(columns=[c for c in ['調定数', '取り付け数'] if c in df_usage.columns])

    # 分析対象の選択
    st.header("🔍 Analysis Settings")
    selected_ids = st.multiselect("分析対象の料金表番号", options=df_master_all['料金表番号'].unique(), default=df_master_all['料金表番号'].unique())
    
    if selected_ids:
        df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
        df_m_sub = df_master_all[df_master_all['料金表番号'].isin(selected_ids)].copy()

        # シミュレーション実行
        df_target_usage['現行料金'] = df_target_usage.apply(lambda x: calculate_fee(x['使用量'], df_master_all[df_master_all['料金表番号']==x['料金表番号']]), axis=1)
        
        # 提案プラン設定 (元コードのロジック維持)
        st.markdown("---")
        st.subheader("💡 Proposal Strategy")
        c1, c2 = st.columns(2)
        with c1:
            base_adj = st.number_input("基本料金 調整額(円)", value=0, step=100)
        with c2:
            unit_adj = st.number_input("従量単価 調整額(円)", value=-10.0, step=0.5)
        
        df_m_prop = df_m_sub.copy()
        df_m_prop['基本料金'] += base_adj
        df_m_prop['従量単価'] += unit_adj
        
        df_target_usage['提案料金'] = df_target_usage.apply(lambda x: calculate_fee(x['使用量'], df_m_prop[df_m_prop['料金表番号']==x['料金表番号']]), axis=1)
        df_target_usage['差額'] = df_target_usage['提案料金'] - df_target_usage['現行料金']

        # メトリクス表示
        m1, m2, m3 = st.columns(3)
        m1.metric("対象件数", f"{len(df_target_usage):,} 件")
        m2.metric("現行総収益", f"¥{df_target_usage['現行料金'].sum():,.0f}")
        m3.metric("改定後影響", f"¥{df_target_usage['差額'].sum():,.0f}", delta_color="inverse")

        # 4. 結果のCSV出力ボタン
        st.markdown("---")
        st.subheader("📊 Results & Export")
        csv_data = df_target_usage.to_csv(index=False).encode('utf-8-sig')
        st.download_button("シミュレーション結果(CSV)を保存", csv_data, f"Gasio_Pro_Result_{datetime.datetime.now().strftime('%Y%m%d')}.csv")

        # 可視化 (件数集計を「調定数」から「count」に変更)
        g1, g2 = st.columns(2)
        with g1:
            st.write("**現行分布**")
            # 1つの料金表が選ばれている場合のみ区画表示
            if len(selected_ids) == 1:
                m_rep = df_master_all[df_master_all['料金表番号'] == selected_ids[0]]
                df_target_usage['区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, m_rep))
                agg = df_target_usage.groupby('区画').size().reset_index(name='件数')
                st.plotly_chart(px.pie(agg, values='件数', names='区画', hole=0.4, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
            else:
                st.plotly_chart(px.histogram(df_target_usage, x="使用量", color="料金表番号", nbins=30), use_container_width=True)
        with g2:
            st.write("**影響度分布**")
            st.plotly_chart(px.histogram(df_target_usage, x="差額", nbins=30, color_discrete_sequence=['#e74c3c']), use_container_width=True)

else:
    st.info("サイドバーからCSVをアップロードするか、デモモードをONにしてください。")

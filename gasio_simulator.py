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

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    .stAlert { padding: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">Gasio計算機 <span style="color:#3498db">Pro</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ガス料金シミュレーション・分析プラットフォーム</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義 (ロジック・サンプル出力)
# ---------------------------------------------------------
def normalize_columns(df):
    """列名の名寄せとクリーニング"""
    rename_map = {
        '料金表ID': '料金表番号', '料金表コード': '料金表番号',
        '顧客ID': '顧客番号',
        '月間使用量': '使用量', '当月使用量': '使用量'
    }
    df = df.rename(columns=rename_map)
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(r'[¥,]', '', regex=True)
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass
    return df

def get_sample_usage_csv():
    """使用量データのサンプルCSV"""
    df = pd.DataFrame({
        '料金表番号': ['A01', 'A01', 'B02', 'B02'],
        '使用量': [12.5, 25.0, 5.0, 45.3]
    })
    return df.to_csv(index=False).encode('utf-8-sig')

def get_sample_master_csv():
    """料金表マスタのサンプルCSV"""
    df = pd.DataFrame({
        '料金表番号': ['A01', 'A01', 'A01', 'B02', 'B02'],
        '料金表名': ['一般料金', '一般料金', '一般料金', 'ゆったりプラン', 'ゆったりプラン'],
        'MAX': [10, 50, 999999, 20, 999999],
        '基本料金': [1000, 1200, 1500, 800, 1000],
        '従量単価': [200, 180, 150, 220, 190]
    })
    return df.to_csv(index=False).encode('utf-8-sig')

def calculate_gas_fee(usage, master_df):
    """特定の料金表マスタに基づいた計算"""
    # 使用量に対応する区画を特定
    tier = master_df[master_df['MAX'] >= usage].sort_values('MAX').iloc[0]
    fee = tier['基本料金'] + (usage * tier['従量単価'])
    return round(fee, 0), tier['基本料金'], tier['従量単価']

# ---------------------------------------------------------
# 3. サイドバー: インポートガイダンス & ファイルアップロード
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    
    with st.expander("ℹ️ CSVインポートガイダンス", expanded=False):
        st.markdown("""
        **1. 使用量CSV**
        - `料金表番号`: マスタと紐づくID
        - `使用量`: 1ヶ月のガス使用量
        ※「調定数」「取り付け数」は不要です。
        
        **2. 料金表マスタCSV**
        - `料金表番号`: ID
        - `MAX`: 区画の上限（例: 10, 50, 999999）
        - `基本料金`, `従量単価`
        """)
        st.download_button("使用量サンプルDL", get_sample_usage_csv(), "sample_usage.csv", "text/csv")
        st.download_button("マスタサンプルDL", get_sample_master_csv(), "sample_master.csv", "text/csv")

    u_file = st.file_uploader("使用量CSVをアップロード", type="csv")
    m_file = st.file_uploader("料金表マスタCSVをアップロード", type="csv")

# ---------------------------------------------------------
# 4. メインロジック
# ---------------------------------------------------------
if u_file and m_file:
    # データ読み込み
    try:
        df_usage = normalize_columns(pd.read_csv(u_file, encoding='utf-8-sig'))
        df_master = normalize_columns(pd.read_csv(m_file, encoding='utf-8-sig'))
        
        # 1. 使用量CSVから「調定数」「取り付け数」を削除
        cols_to_drop = ['調定数', '取り付け数']
        df_usage = df_usage.drop(columns=[c for c in cols_to_drop if c in df_usage.columns])

        st.success("データの読み込みに成功しました。")

        # シミュレーション設定（簡易版）
        st.subheader("📊 シミュレーション設定")
        target_ids = st.multiselect("分析対象の料金表番号", options=df_master['料金表番号'].unique(), default=df_master['料金表番号'].unique())
        
        if target_ids:
            df_target_usage = df_usage[df_usage['料金表番号'].isin(target_ids)].copy()
            
            # 料金計算実行
            def run_sim(row):
                m_sub = df_master[df_master['料金表番号'] == row['料金表番号']]
                if m_sub.empty: return 0
                fee, _, _ = calculate_gas_fee(row['使用量'], m_sub)
                return fee

            df_target_usage['現行料金'] = df_target_usage.apply(run_sim, axis=1)

            # 結果表示
            st.metric("対象件数", f"{len(df_target_usage):,} 件")
            st.dataframe(df_target_usage.head(100), use_container_width=True)

            # 4. シミュレーション結果をCSV出力
            st.subheader("💾 結果の書き出し")
            csv_result = df_target_usage.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="シミュレーション結果をCSVで保存",
                data=csv_result,
                file_name=f"sim_result_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")

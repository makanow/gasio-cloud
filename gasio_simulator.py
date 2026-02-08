import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------------------------------------------------
# 1. 共通設定・スタイル
# ---------------------------------------------------------
st.set_page_config(page_title="GasIO Simulator", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ヘルパー関数
# ---------------------------------------------------------

def normalize_columns(df):
    """カラム名の揺れを吸収する"""
    rename_map = {
        '料金表No': '料金表番号', 'No': '料金表番号', 'ID': '料金表番号',
        '月間使用量': '使用量', '数量': '使用量',
        '世帯数': '調定数', '件数': '調定数', '口数': '調定数'
    }
    return df.rename(columns=rename_map)

def calculate_gas_bill(usage, tariff_master):
    """
    指定された使用量と料金表マスタからガス料金を計算するロジック。
    """
    master = tariff_master[tariff_master['料金表番号'] == usage['料金表番号']]
    if master.empty:
        return np.nan
    
    # 区画の判定 (MIN <= 使用量 < MAX)
    row = master[(usage['使用量'] >= master['MIN']) & (usage['使用量'] < master['MAX'])]
    if row.empty:
        row = master[usage['使用量'] >= master['MIN']].sort_values('MIN', ascending=False).head(1)

    if not row.empty:
        base_fee = row.iloc[0]['基本料金']
        unit_price = row.iloc[0]['単位料金']
        bill = (base_fee + (usage['使用量'] * unit_price)) * usage['調定数']
        return int(np.floor(bill)) 
    return np.nan

def get_sample_csv(csv_type="usage"):
    """テンプレートデータを作成する"""
    if csv_type == "usage":
        df = pd.DataFrame({
            '料金表番号': [10, 10, 10, 11, 11],
            '使用量': [15.5, 24.0, 8.2, 5.0, 45.3],
            '調定数': [1, 1, 1, 1, 1]
        })
    else: # master
        df = pd.DataFrame({
            '料金表番号': [10, 10, 10, 11, 11, 11],
            '区画': ['A', 'B', 'C', 'A', 'B', 'C'],
            'MIN': [0.0, 8.0, 30.0, 0.0, 10.0, 50.0],
            'MAX': [8.0, 30.0, 99999.0, 10.0, 50.0, 99999.0],
            '基本料金': [1500, 2300, 5300, 1800, 2800, 6800],
            '単位料金': [500.0, 400.0, 300.0, 550.0, 450.0, 350.0]
        })
    return df.to_csv(index=False).encode('utf-8-sig')

# ---------------------------------------------------------
# 3. サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.title("🚀 GasIO Pro")
    st.info("Gas Lab 料金比較シミュレーター")
    
    st.header("📂 1. データインポート")
    
    with st.expander("📥 テンプレートをダウンロード"):
        st.download_button(
            label="1. 使用量CSVテンプレート",
            data=get_sample_csv("usage"),
            file_name="template_usage.csv",
            mime="text/csv",
        )
        st.download_button(
            label="2. 料金表マスタテンプレート",
            data=get_sample_csv("master"),
            file_name="template_master.csv",
            mime="text/csv",
        )
    st.markdown("---")

    uploaded_usage = st.file_uploader("使用量データ (CSV)", type=['csv'])
    uploaded_master = st.file_uploader("料金表マスタ (CSV)", type=['csv'])

# ---------------------------------------------------------
# 4. メインコンテンツ
# ---------------------------------------------------------
st.title("📊 料金比較シミュレーション")

if uploaded_usage and uploaded_master:
    df_usage = normalize_columns(pd.read_csv(uploaded_usage))
    df_master = normalize_columns(pd.read_csv(uploaded_master))

    with st.spinner("計算中..."):
        df_usage['最終料金'] = df_usage.apply(
            lambda x: calculate_gas_bill(x, df_master), axis=1
        )
        df_usage['最終料金'] = df_usage['最終料金'].fillna(0).astype(int)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総調定数", f"{df_usage['調定数'].sum():,} 件")
    with col2:
        st.metric("総販売量", f"{df_usage['使用量'].sum():,.1f} m3")
    with col3:
        st.metric("推定総売上", f"¥{df_usage['最終料金'].sum():,} ")

    st.subheader("📈 使用量 vs 料金 分布")
    fig = px.scatter(df_usage, x="使用量", y="最終料金", color="料金表番号", 
                     hover_data=['料金表番号', '使用量', '最終料金'])
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📝 計算結果の詳細を確認"):
        st.dataframe(df_usage, use_container_width=True)

    csv_output = df_usage.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="✅ 結果をダウンロード",
        data=csv_output,
        file_name="simulation_result.csv",
        mime="text/csv",
    )
else:
    st.warning("サイドバーからデータをアップロードしてください。")
    st.markdown("""
    ### 💡 使い方
    1. **テンプレートをダウンロード**: サイドバーのボタンからCSVのレイアウトを確認してください。
    2. **データをアップロード**: お手持ちのCSVを選択します。
    3. **結果確認**: 自動的に計算結果が表示されます。
    """)

# ---------------------------------------------------------
# 5. フッター
# ---------------------------------------------------------
st.markdown("---")
st.caption("Gas Lab: 地域インフラ企業の持続可能性を支える")

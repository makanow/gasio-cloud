import streamlit as st
import pandas as pd
import numpy as np
import json
import base64
import io
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. 共通設定・スタイル
# ---------------------------------------------------------
st.set_page_config(page_title="GasIO Simulator", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .reportview-container .main .block-container{ padding-top: 2rem; }
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
    ナガセの「泥臭い真実（1円の狂いもない計算）」を支える心臓部だ。
    """
    # 該当する料金表番号のフィルタリング
    master = tariff_master[tariff_master['料金表番号'] == usage['料金表番号']]
    if master.empty:
        return np.nan
    
    # 区画の判定 (MIN <= 使用量 < MAX)
    row = master[(usage['使用量'] >= master['MIN']) & (usage['使用量'] < master['MAX'])]
    if row.empty:
        # MAXが99999などの最終区画対応
        row = master[usage['使用量'] >= master['MIN']].sort_values('MIN', ascending=False).head(1)

    if not row.empty:
        base_fee = row.iloc[0]['基本料金']
        unit_price = row.iloc[0]['単位料金']
        # 計算式: (基本料金 + 使用量 * 単位料金) * 調定数
        # 消費税等の扱いは必要に応じてここで調整
        bill = (base_fee + (usage['使用量'] * unit_price)) * usage['調定数']
        return int(np.floor(bill)) # 1円未満切り捨て
    return np.nan

# --- 追加: サンプルCSV生成用関数 ---
def get_sample_csv(csv_type="usage"):
    """ユーザーに提供する雛形データを作成する"""
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
    # Excelで開いても文字化けしないよう utf-8-sig を採用
    return df.to_csv(index=False).encode('utf-8-sig')

# ---------------------------------------------------------
# 3. サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.title("🚀 GasIO Pro")
    st.info("Gas Lab 事業構想に基づく料金比較シミュレーター")
    
    st.header("📂 1. データインポート")
    
    # --- 追加: ダウンロードボタンの設置 ---
    with st.expander("📥 雛形CSVをダウンロード"):
        st.caption("CSVのレイアウトが不明な場合は以下をご利用ください")
        st.download_button(
            label="1. 使用量CSVサンプル",
            data=get_sample_csv("usage"),
            file_name="sample_usage.csv",
            mime="text/csv",
        )
        st.download_button(
            label="2. 料金表マスタサンプル",
            data=get_sample_csv("master"),
            file_name="sample_master.csv",
            mime="text/csv",
        )
    st.markdown("---")

    uploaded_usage = st.file_uploader("使用量データ (CSV)", type=['csv'])
    uploaded_master = st.file_uploader("料金表マスタ (CSV)", type=['csv'])
    
    st.header("⚙️ 2. パラメータ調整")
    tax_rate = st.slider("消費税率 (%)", 0, 15, 10)
    fuel_adj = st.number_input("燃料費調整額 (円/m3)", value=0.0, step=0.1)

# ---------------------------------------------------------
# 4. メインコンテンツ
# ---------------------------------------------------------
st.title("📊 料金比較シミュレーション")

if uploaded_usage and uploaded_master:
    # データの読み込み
    df_usage = normalize_columns(pd.read_csv(uploaded_usage))
    df_master = normalize_columns(pd.read_csv(uploaded_master))

    st.success("データの読み込みに成功しました。")

    # 計算実行
    with st.spinner("計算中..."):
        df_usage['計算料金'] = df_usage.apply(
            lambda x: calculate_gas_bill(x, df_master), axis=1
        )
        # 燃調分と消費税の加算（簡易実装）
        df_usage['最終料金'] = (df_usage['計算料金'] + (df_usage['使用量'] * fuel_adj)) * (1 + tax_rate/100)
        df_usage['最終料金'] = df_usage['最終料金'].fillna(0).astype(int)

    # 指標の表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総調定数", f"{df_usage['調定数'].sum():,} 件")
    with col2:
        st.metric("総販売量", f"{df_usage['使用量'].sum():,.1f} m3")
    with col3:
        st.metric("推定総売上", f"¥{df_usage['最終料金'].sum():,} ")

    # グラフ表示
    st.subheader("📈 使用量 vs 料金 分布")
    fig = px.scatter(df_usage, x="使用量", y="最終料金", color="料金表番号", 
                     hover_data=['料金表番号', '使用量', '最終料金'],
                     title="顧客ごとの料金分布")
    st.plotly_chart(fig, use_container_width=True)

    # 詳細テーブル
    with st.expander("📝 計算結果の詳細を確認"):
        st.dataframe(df_usage, use_container_width=True)

    # エクスポート
    csv_output = df_usage.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="✅ シミュレーション結果をダウンロード",
        data=csv_output,
        file_name="simulation_result.csv",
        mime="text/csv",
    )

else:
    st.warning("左側のサイドバーから「使用量データ」と「料金表マスタ」をアップロードしてください。")
    
    # イントロダクション
    st.markdown("""
    ### 💡 使い方
    1. **雛形CSVをダウンロード**: 初めての方はサイドバーの「雛形CSV」を参考にデータを作成してください。
    2. **データをアップロード**: お手持ちの使用量CSVと料金マスタCSVを選択します。
    3. **パラメータ設定**: 税率や燃料費調整額を調整します。
    4. **結果確認**: 自動的に計算が行われ、分布グラフと総売上が表示されます。
    """)

# ---------------------------------------------------------
# 5. フッター (Gas Lab 原則)
# ---------------------------------------------------------
st.markdown("---")
st.caption("Gas Lab: 「100名の壁」を支える、地域インフラ企業のシェアード・ブレイン")

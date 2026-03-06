import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px

st.set_page_config(layout="wide", page_title="Gasio Cluster AI")
st.title("🤖 Gasio Cluster: 滝川データ解析エディション")

# --- 🛠️ サイドバー ---
with st.sidebar:
    st.header("📂 データ入力")
    file_master = st.file_uploader("① 滝川料金表マスタ", type='csv')
    file_usage = st.file_uploader("② 滝川請求データ", type='csv')
    
    if file_master and file_usage:
        st.divider()
        st.header("⚙️ 解析パラメーター")
        k = st.slider("統合後の目標グループ数", 2, 10, 5)
        low_usage_threshold = st.slider("低使用量層の定義 (m3)", 5, 40, 10, step=5)

# --- 📈 メイン画面 ---
if file_master and file_usage:
    df_m = pd.read_csv(file_master)
    df_u = pd.read_csv(file_usage)

    # 1. 列名の名寄せ（滝川仕様）
    df_u = df_u.rename(columns={'使用量': '当月使用量'})
    # マスタ側：料金プランIDをキーにする
    df_m = df_m.rename(columns={'料金プランID': '料金表番号'})

    # 2. 料金計算ロジック（マスタの区画に合わせて金額を算出）
    def calculate_amount(row, master):
        plan_id = row['料金表番号']
        usage = row['当月使用量']
        # 該当するプランの区画を特定
        m = master[master['料金表番号'] == plan_id]
        if m.empty: return 0
        # 使用量が上限・下限に収まる区画を探す
        target = m[(m['下限'] <= usage) & (m['上限'] >= usage)]
        if target.empty:
            target = m.iloc[[-1]] # 収まらなければ最後の区画
        
        base_fee = target.iloc[0]['基本料金']
        unit_price = target.iloc[0]['従量単価']
        return base_fee + (usage * unit_price)

    # 実績データに金額を付与
    df_u['当月金額'] = df_u.apply(calculate_amount, axis=1, master=df_m)

    # 3. 特徴量抽出
    def calc_low_ratio(x):
        active = (x > 0).sum()
        return ((x > 0) & (x <= low_usage_threshold)).sum() / active if active > 0 else 0

    df_features = df_u.groupby('料金表番号').agg({
        '当月使用量': ['mean', calc_low_ratio],
        '当月金額': 'mean'
    }).reset_index()
    
    df_features.columns = ['料金表番号', '平均使用量(m3)', '低使用量層の割合', '平均金額']
    df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)'].replace(0, 1)

    # 4. AIクラスタリング
    X = df_features[['平均使用量(m3)', '低使用量層の割合', '実質単価(円/m3)']].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=k, random_state=42)
    df_features['新グループ'] = [chr(65 + i) for i in kmeans.fit_predict(X_scaled)]

    # --- 3Dマップ ---
    st.subheader("🌌 AIの脳内マップ")
    fig = px.scatter_3d(
        df_features, x='平均使用量(m3)', y='低使用量層の割合', z='実質単価(円/m3)',
        color='新グループ', hover_name='料金表番号',
        color_discrete_sequence=px.colors.qualitative.Pastel, height=700
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 結果表 ---
    st.header("✨ AI集約提案結果")
    summary = df_features.groupby('新グループ').agg({
        '料金表番号': lambda x: ', '.join(x.astype(str)),
        '平均使用量(m3)': 'mean',
        '実質単価(円/m3)': 'mean',
        '平均金額': 'mean'
    }).reset_index()
    
    # 代表的な基本料金を1500円と仮定して逆算
    summary['参考基本料金'] = 1500.0 
    summary['参考従量単価'] = (summary['平均金額'] - 1500) / summary['平均使用量(m3)'].replace(0, 1)
    
    disp_summary = summary.drop(columns=['平均金額']).rename(columns={'料金表番号': '統合対象ID'})
    st.table(disp_summary.style.format({
        '平均使用量(m3)': '{:,.1f}', '実質単価(円/m3)': '{:,.1f}',
        '参考基本料金': '{:,.1f}', '参考従量単価': '{:,.1f}'
    }).set_properties(**{'text-align': 'right'}, subset=['平均使用量(m3)', '実質単価(円/m3)', '参考基本料金', '参考従量単価']))

    # エクスポート
    with st.sidebar:
        st.divider()
        csv = disp_summary.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 指示書(CSV)を出す", csv, "gasio_ai_proposal.csv", use_container_width=True)

else:
    st.info("👈 左側のサイドバーから「滝川料金表マスタ」と「滝川請求データ」をアップロードしてください。")

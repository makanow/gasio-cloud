import streamlit as st
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px

# ページ全体のレイアウト設定
st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

st.title("🤖 Gasio Cluster: AI料金集約エンジン")

# --- 🛠️ サイドバー：2つのファイルを管理 ---
with st.sidebar:
    st.header("📂 データ入力")
    # 1. 料金表マスターの読み込み
    file_master = st.file_uploader("① 料金表マスター(CSV)をアップロード", type='csv')
    # 2. 実績データの読み込み
    file_usage = st.file_uploader("② 実績データ(CSV)をアップロード", type='csv')
    
    if file_master and file_usage:
        st.success("2つのファイルを認識しました")
        st.divider()
        st.header("⚙️ 解析パラメーター")
        
        k = st.slider("統合後の目標グループ数", 2, 10, 5)
        low_usage_threshold = st.slider("低使用量層の定義 (m3)", 5, 40, 10, step=5)
        st.caption(f"0.1 ～ {low_usage_threshold}m3 を「低使用量層」と定義")

# --- 📈 メイン画面：解析・表示エリア ---
if file_master and file_usage:
    # データの読み込み
    df_m = pd.read_csv(file_master)
    df_u = pd.read_csv(file_usage)

    # ステップ1: データの結合（料金表番号をキーにする）
    # 実績データに料金表名や現在の単価を紐付け
    df_merged = pd.merge(df_u, df_m, on='料金表番号', how='left')

    # ステップ2: 特徴量の抽出（スライダーの値を反映）
    def calc_low_ratio(x):
        active = (x > 0).sum()
        if active == 0: return 0
        return ((x > 0) & (x <= low_usage_threshold)).sum() / active

    df_features = df_merged.groupby('料金表番号').agg({
        '当月使用量': ['mean', calc_low_ratio],
        '当月金額': 'mean'
    }).reset_index()
    
    df_features.columns = ['料金表番号', '平均使用量(m3)', '低使用量層の割合', '平均金額']
    df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)']

    # ステップ3: AIクラスタリング
    features_for_clustering = ['平均使用量(m3)', '低使用量層の割合', '実質単価(円/m3)']
    X = df_features[features_for_clustering].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=k, random_state=42)
    df_features['新グループ'] = kmeans.fit_predict(X_scaled)
    df_features['新グループ'] = df_features['新グループ'].apply(lambda x: chr(65 + x))

    # --- 可視化：3Dマップ ---
    st.subheader("🌌 AIの脳内マップ（3Dクラスタリング空間）")
    fig = px.scatter_3d(
        df_features, x='平均使用量(m3)', y='低使用量層の割合', z='実質単価(円/m3)',
        color='新グループ', hover_name='料金表番号',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        height=700
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 集計：AI集約提案結果 ---
    st.header("✨ AI集約提案結果")
    summary = df_features.groupby('新グループ').agg({
        '料金表番号': lambda x: ', '.join(x.astype(str)),
        '平均使用量(m3)': 'mean',
        '実質単価(円/m3)': 'mean',
        '平均金額': 'mean'
    }).reset_index()
    
    # 既存の料金表から「基本料金」の平均を参考値として持ってくる等の処理
    summary['参考基本料金'] = 1500.0 
    summary['参考従量単価'] = (summary['平均金額'] - 1500) / summary['平均使用量(m3)']
    summary.rename(columns={'料金表番号': '統合対象の現行プランID'}, inplace=True)

    # 表の表示
    styled_summary = summary.drop(columns=['平均金額']).style.format({
        '平均使用量(m3)': '{:,.1f}', '実質単価(円/m3)': '{:,.1f}',
        '参考基本料金': '{:,.1f}', '参考従量単価': '{:,.1f}'
    }).set_properties(**{'text-align': 'right'}, subset=['平均使用量(m3)', '実質単価(円/m3)', '参考基本料金', '参考従量単価'])
    
    st.table(styled_summary)

    # --- エクスポート ---
    with st.sidebar:
        st.divider()
        csv_data = summary.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 指示書(CSV)を出す",
            data=csv_data,
            file_name="gasio_ai_proposal.csv",
            use_container_width=True
        )
else:
    # ファイルが足りない時の案内
    st.info("👈 左側のサイドバーから「料金表マスター」と「実績データ」の2つをアップロードしてください。")

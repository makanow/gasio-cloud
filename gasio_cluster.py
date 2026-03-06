import streamlit as st
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px

# ページ設定（広く使う）
st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

st.title("🤖 Gasio Cluster: AI料金集約エンジン")

# --- 🛠️ サイドバー：入力・操作エリア ---
with st.sidebar:
    st.header("📂 データ入力")
    uploaded_file = st.file_uploader("実績CSVをアップロード", type='csv')
    
    if uploaded_file:
        st.success("CSV読み込み完了")
        
        st.divider()
        st.header("⚙️ 解析パラメーター")
        
        # 1. グループ数の調整
        k = st.slider("統合後の目標グループ数", 2, 10, 5)
        
        # 2. 低使用量層の定義（動的）
        low_usage_threshold = st.slider("低使用量層の定義 (m3)", 5, 40, 10, step=5)
        st.caption(f"0.1 ～ {low_usage_threshold}m3 を「低使用量層」と定義")
        
        st.divider()
        st.info("設定を変更すると、右側の解析結果がリアルタイムで更新されます。")

# --- 📈 メイン画面：解析・表示エリア ---
if uploaded_file:
    # データ読み込み
    df_usage = pd.read_csv(uploaded_file)

    # ステップ2: 特徴量の抽出（スライダーの値を反映）
    def calc_low_ratio(x):
        active = (x > 0).sum()
        return ((x > 0) & (x <= low_usage_threshold)).sum() / active if active > 0 else 0

    df_features = df_usage.groupby('料金表番号').agg({
        '当月使用量': ['mean', calc_low_ratio],
        '当月金額': 'mean'
    }).reset_index()
    
    df_features.columns = ['料金表番号', '平均使用量(m3)', '低使用量層の割合', '平均金額']
    df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)']

    # ステップ3: AIクラスタリング (K-Means)
    features_for_clustering = ['平均使用量(m3)', '低使用量層の割合', '実質単価(円/m3)']
    X = df_features[features_for_clustering]
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
        height=600
    )
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- 集計：AI集約提案結果 ---
    st.header("✨ AI集約提案結果")
    summary = df_features.groupby('新グループ').agg({
        '料金表番号': lambda x: ', '.join(x.astype(str)),
        '平均使用量(m3)': 'mean',
        '実質単価(円/m3)': 'mean',
        '平均金額': 'mean' # ベース単価計算用
    }).reset_index()
    
    # 簡易的な基本料金・従量単価の逆算（仮説値）
    summary['基本料金'] = 1500.0 # 仮の初期値
    summary['従量単価'] = (summary['平均金額'] - 1500) / summary['平均使用量(m3)']
    summary.rename(columns={'料金表番号': '統合対象の現行プランID'}, inplace=True)

    # 表のスタイリングと表示
    styled_summary = summary.drop(columns=['平均金額']).style.format({
        '平均使用量(m3)': '{:,.1f}', '実質単価(円/m3)': '{:,.1f}',
        '基本料金': '{:,.1f}', '従量単価': '{:,.1f}'
    }).set_properties(**{'text-align': 'right'}, subset=['平均使用量(m3)', '実質単価(円/m3)', '基本料金', '従量単価'])
    
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
    st.info("左側のサイドバーから実績CSVをアップロードしてください。")

import streamlit as st
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px

# 1. ページ設定
st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

st.title("🤖 Gasio Cluster: AI料金集約エンジン")

# --- 🛠️ サイドバー：入力・操作エリア ---
with st.sidebar:
    st.header("📂 データ入力")
    file_master = st.file_uploader("① 料金表マスター(CSV)", type='csv')
    file_usage = st.file_uploader("② 実績データ(CSV)", type='csv')
    
    if file_master and file_usage:
        st.success("2つのファイルを認識しました")
        st.divider()
        st.header("⚙️ 解析パラメーター")
        k = st.slider("統合後の目標グループ数", 2, 10, 5)
        low_usage_threshold = st.slider("低使用量層の定義 (m3)", 5, 40, 10, step=5)

# --- 📈 メイン画面：解析エリア ---
if file_master and file_usage:
    # CSV読み込み
    df_m = pd.read_csv(file_master)
    df_u = pd.read_csv(file_usage)

    # 【重要】エラー回避：列名の「揺れ」を自動補正する
    def fix_col_names(df):
        # よくある名前を「料金表番号」に統一
        rename_dict = {
            '料金表No': '料金表番号', '料金表コード': '料金表番号', 
            'プラン番号': '料金表番号', '料金表ID': '料金表番号'
        }
        df = df.rename(columns=rename_dict)
        # もし「料金表番号」がなければ、一番左の列を強制的にそれとみなす
        if '料金表番号' not in df.columns:
            df.rename(columns={df.columns[0]: '料金表番号'}, inplace=True)
        return df

    df_m = fix_col_names(df_m)
    df_u = fix_col_names(df_u)

    # データの結合
    try:
        df_merged = pd.merge(df_u, df_m, on='料金表番号', how='left')
    except Exception as e:
        st.error(f"データの結合（マージ）に失敗しました。列名を確認してください。: {e}")
        st.stop()

    # 特徴量抽出
    def calc_low_ratio(x):
        active = (x > 0).sum()
        return ((x > 0) & (x <= low_usage_threshold)).sum() / active if active > 0 else 0

    df_features = df_merged.groupby('料金表番号').agg({
        '当月使用量': ['mean', calc_low_ratio],
        '当月金額': 'mean'
    }).reset_index()
    
    df_features.columns = ['料金表番号', '平均使用量(m3)', '低使用量層の割合', '平均金額']
    # 0除算対策
    df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)'].replace(0, 1)

    # AIクラスタリング
    X = df_features[['平均使用量(m3)', '低使用量層の割合', '実質単価(円/m3)']].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=k, random_state=42)
    df_features['新グループ'] = [chr(65 + i) for i in kmeans.fit_predict(X_scaled)]

    # 3Dマップ表示
    st.subheader("🌌 AIの脳内マップ")
    fig = px.scatter_3d(
        df_features, x='平均使用量(m3)', y='低使用量層の割合', z='実質単価(円/m3)',
        color='新グループ', hover_name='料金表番号',
        color_discrete_sequence=px.colors.qualitative.Pastel, height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    # 結果表の表示
    st.header("✨ AI集約提案結果")
    summary = df_features.groupby('新グループ').agg({
        '料金表番号': lambda x: ', '.join(x.astype(str)),
        '平均使用量(m3)': 'mean',
        '実質単価(円/m3)': 'mean',
        '平均金額': 'mean'
    }).reset_index()
    
    # 簡易計算（基本料金は仮定）
    summary['参考基本料金'] = 1500.0 
    summary['参考従量単価'] = (summary['平均金額'] - 1500) / summary['平均使用量(m3)'].replace(0, 1)
    
    # 表示用に整形
    disp_summary = summary.drop(columns=['平均金額']).rename(columns={'料金表番号': '統合対象ID'})
    st.table(disp_summary.style.format({
        '平均使用量(m3)': '{:,.1f}', '実質単価(円/m3)': '{:,.1f}',
        '参考基本料金': '{:,.1f}', '参考従量単価': '{:,.1f}'
    }).set_properties(**{'text-align': 'right'}, subset=['平均使用量(m3)', '実質単価(円/m3)', '参考基本料金', '参考従量単価']))

    # CSV出力
    with st.sidebar:
        st.divider()
        csv = disp_summary.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 指示書(CSV)を出す", csv, "gasio_ai_proposal.csv", use_container_width=True)

else:
    st.info("👈 左のサイドバーから「料金表」と「実績」の2ファイルをアップロードしてください。")

import streamlit as st
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np
import plotly.express as px

# --- ページ設定 ---
st.set_page_config(page_title="Gasio Cluster (AI料金集約エンジン)", layout="wide")
st.title("🤖 Gasio Cluster - 料金プランAI集約エンジン")
st.markdown("Gasio計算機Proからエクスポートした「料金表マスタ」と「請求データ」をアップロードし、最適な統合プランをAIが提案します。")

# --- ファイルアップロード ---
col1, col2 = st.columns(2)
with col1:
    master_file = st.file_uploader("1. 料金表マスタをアップロード", type=["csv"])
with col2:
    billing_file = st.file_uploader("2. 請求データをアップロード", type=["csv"])

if master_file is not None and billing_file is not None:
    st.success("データの読み込みに成功しました。AI解析を開始します...")

    # データ読み込み
    df_master = pd.read_csv(master_file)
    df_billing = pd.read_csv(billing_file)

    # --- ステップ1: 請求データからの特徴量抽出（需要構成） ---
    # プランごとの平均使用量
    plan_usage = df_billing.groupby('料金表番号')['使用量'].mean().reset_index()
    plan_usage.rename(columns={'使用量': '平均使用量(m3)'}, inplace=True)

    # プランごとの0〜10m3の割合（ボリュームゾーン指標）
    df_billing['0_10m3_フラグ'] = np.where(df_billing['使用量'] <= 10, 1, 0)
    plan_vol = df_billing.groupby('料金表番号')['0_10m3_フラグ'].mean().reset_index()
    plan_vol.rename(columns={'0_10m3_フラグ': '低使用量層の割合'}, inplace=True)

    # --- ステップ2: 料金表マスタからの特徴量抽出（実質単価） ---
    # 今回は簡略化のため、各プランの「区画A（最小区画）」の単価をベースラインとして抽出
    df_master_base = df_master.drop_duplicates(subset=['料金プランID'], keep='first')
    df_master_features = df_master_base[['料金プランID', '基本料金', '従量単価']].copy()
    df_master_features.rename(columns={'料金プランID': '料金表番号'}, inplace=True)

    # --- データ結合 ---
    df_features = pd.merge(plan_usage, plan_vol, on='料金表番号', how='inner')
    df_features = pd.merge(df_features, df_master_features, on='料金表番号', how='inner')

    # 実質平均単価（推定）= (基本料金 / 平均使用量) + 従量単価
    df_features['実質単価(円/m3)'] = (df_features['基本料金'] / df_features['平均使用量(m3)']) + df_features['従量単価']

    st.subheader("📊 抽出された各プランの特徴量（AIのインプット）")
    st.dataframe(df_features)

    # --- ステップ3: AIによるクラスタリング（K-Means法） ---
    cluster_num = st.slider("統合するグループ（新プラン）の数を選択してください", min_value=2, max_value=10, value=5)
    
    # 機械学習用にデータを正規化（スケール合わせ）
    features_for_ai = df_features[['平均使用量(m3)', '低使用量層の割合', '実質単価(円/m3)']]
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features_for_ai)

    # K-Means実行
    kmeans = KMeans(n_clusters=cluster_num, random_state=42)
    df_features['新グループ'] = kmeans.fit_predict(scaled_features)
    # 分かりやすくA, B, C...に変換
    df_features['新グループ'] = df_features['新グループ'].apply(lambda x: chr(65 + x)) 
    
    # --- ステップ3.5: AIの脳内宇宙（3D可視化） ---
    st.subheader("🌌 AIの脳内マップ（3Dクラスタリング空間）")
    st.markdown("各点が1つの現行料金プラン（料金表番号）を表します。同じ色の玉は、AIが「DNAが似ている」と判断して同じグループに分類したものです。**マウスでドラッグして宇宙を回し、各点にカーソルを合わせてみてください。**")

    fig = px.scatter_3d(
        df_features,
        x='平均使用量(m3)',
        y='低使用量層の割合',
        z='実質単価(円/m3)',
        color='新グループ',
        hover_name='料金表番号', # マウスを乗せたらプラン番号が出る
        hover_data={'新グループ': True, '平均使用量(m3)': ':.1f', '低使用量層の割合': ':.1%', '実質単価(円/m3)': ':.1f'},
        color_discrete_sequence=px.colors.qualitative.Pastel # 見やすい配色
    )

    # グラフの余白を削ってダイナミックに表示
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0), height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    # --- ステップ4: 解析結果の表示 ---
    st.header("✨ AI集約提案結果")
    
    # グループごとのサマリー
    summary = df_features.groupby('新グループ').agg({
        '料金表番号': lambda x: ', '.join(x.astype(str)),
        '平均使用量(m3)': 'mean',
        '実質単価(円/m3)': 'mean',
        '基本料金': 'mean',
        '従量単価': 'mean'
    }).reset_index()
    summary.rename(columns={'料金表番号': '統合対象の現行プランID'}, inplace=True)

    st.markdown("以下の表は、**AIが「需要の形」と「価格」が似ているものを自動でまとめた結果**です。これがGasio計算機Proへ打ち込むべき新プランのベースとなります。")
    formatted_summary = summary.copy()
numeric_cols = ['平均使用量(m3)', '実質単価(円/m3)', '基本料金', '従量単価']

# 各数値を「1,234.5」の形式に変換
for col in numeric_cols:
    formatted_summary[col] = formatted_summary[col].map('{:,.1f}'.format)

st.dataframe(formatted_summary)

    # --- ステップ5: エクスポート機能（Gasio計算機Pro連携用） ---
csv_export = formatted_summary.to_csv(index=False, encoding='utf-8-sig')
st.download_button(
    label="📥 シミュレーション用指示書（CSV）をエクスポート",
    data=csv_export,
    file_name="gasio_ai_cluster_proposal.csv",
    mime="text/csv",
)

import streamlit as st
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px

# 1. ページ全体のレイアウト設定
st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

st.title("🤖 Gasio Cluster: AI料金集約エンジン")

# --- 🛠️ サイドバー：入力・操作エリア ---
with st.sidebar:
    st.header("📂 データ入力")
    file_master = st.file_uploader("① 料金表マスタ(CSV)", type='csv')
    file_usage = st.file_uploader("② 実績データ(CSV)", type='csv')
    
    if file_master and file_usage:
        st.success("2つのファイルを認識しました")
        st.divider()
        st.header("⚙️ 解析パラメーター")
        k = st.slider("統合後の目標グループ数", 2, 10, 5)
        low_usage_threshold = st.slider("低使用量層の定義 (m3)", 5, 40, 10, step=5)

# --- 📈 メイン画面：解析・表示エリア ---
if file_master and file_usage:
    # データの読み込み
    df_m = pd.read_csv(file_master)
    df_u = pd.read_csv(file_usage)

    # 【名称の汎用化とクレンジング】
    # 実績データ側の列名調整
    df_u = df_u.rename(columns={'使用量': '使用量_u', '料金表番号': '料金表番号_u'})
    # マスタ側の列名調整
    df_m = df_m.rename(columns={'料金プランID': '料金表番号_m'})

    # 【高速ベクトル演算による金額計算】
    # 1. マスタと実績をマージ（一度全ての組み合わせを作るが、直後にフィルタリングしてメモリを節約）
    merged = pd.merge(df_u, df_m, left_on='料金表番号_u', right_on='料金表番号_m', how='left')
    
    # 2. 使用量が「下限～上限」の範囲内にある行だけを抽出（スライド料金対応）
    df_calc = merged[(merged['使用量_u'] >= merged['下限']) & (merged['使用量_u'] <= merged['上限'])].copy()
    
    # 3. 金額を計算
    df_calc['当月金額'] = df_calc['基本料金'] + (df_calc['使用量_u'] * df_calc['従量単価'])

    # 【特徴量抽出】
    def calc_low_ratio(x):
        active = (x > 0).sum()
        return ((x > 0) & (x <= low_usage_threshold)).sum() / active if active > 0 else 0

    # プランごとの集計
    df_features = df_calc.groupby(['料金表番号_u', '料金プラン名']).agg({
        '使用量_u': ['mean', calc_low_ratio],
        '当月金額': 'mean'
    }).reset_index()
    
    df_features.columns = ['料金表番号', '料金プラン名', '平均使用量(m3)', '低使用量層の割合', '平均金額']
    df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)'].replace(0, 1)

    # 【AIクラスタリング】
    features = ['平均使用量(m3)', '低使用量層の割合', '実質単価(円/m3)']
    X = df_features[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=k, random_state=42)
    df_features['新グループ'] = [chr(65 + i) for i in kmeans.fit_predict(X_scaled)]

    # --- 可視化：3Dマップ ---
    st.subheader("🌌 AIの脳内マップ（3Dクラスタリング空間）")
    fig = px.scatter_3d(
        df_features, x='平均使用量(m3)', y='低使用量層の割合', z='実質単価(円/m3)',
        color='新グループ', hover_name='料金プラン名',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        height=700
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 集計：AI集約提案結果 ---
    st.header("✨ AI集約提案結果")
    summary = df_features.groupby('新グループ').agg({
        '料金プラン名': lambda x: ' / '.join(x.astype(str)),
        '平均使用量(m3)': 'mean',
        '実質単価(円/m3)': 'mean',
        '平均金額': 'mean'
    }).reset_index()
    
    # 提案用：基本料金を1500円と仮定した逆算
    summary['参考基本料金'] = 1500.0 
    summary['参考従量単価'] = (summary['平均金額'] - 1500) / summary['平均使用量(m3)'].replace(0, 1)
    
    disp_summary = summary.drop(columns=['平均金額']).rename(columns={'料金プラン名': '統合対象の現行プラン'})

    # 右寄せスタイリング
    st.table(disp_summary.style.format({
        '平均使用量(m3)': '{:,.1f}', '実質単価(円/m3)': '{:,.1f}',
        '参考基本料金': '{:,.1f}', '参考従量単価': '{:,.1f}'
    }).set_properties(**{'text-align': 'right'}, subset=['平均使用量(m3)', '実質単価(円/m3)', '参考基本料金', '参考従量単価']))

    # --- エクスポート ---
    with st.sidebar:
        st.divider()
        csv_data = disp_summary.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 シミュレーション用指示書（CSV）",
            data=csv_data,
            file_name="gasio_ai_proposal.csv",
            use_container_width=True
        )
else:
    st.info("👈 左側のサイドバーから「料金表マスタ」と「実績データ」をアップロードしてください。")

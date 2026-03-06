import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px

st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

# --- デモデータ生成関数 ---
def get_demo_data():
    # 料金表マスタ(ダミー)
    master_data = {
        '料金プランID': [1, 1, 2, 2, 3, 3],
        '料金プラン名': ['一般Aプラン', '一般Aプラン', 'ゆったりBプラン', 'ゆったりBプラン', '暖房Cプラン', '暖房Cプラン'],
        '下限': [0, 20, 0, 30, 0, 50],
        '上限': [19.9, 999, 29.9, 999, 49.9, 999],
        '基本料金': [1000, 1500, 1200, 1800, 2000, 2500],
        '従量単価': [200, 180, 190, 170, 150, 130]
    }
    # 実績データ(ダミー)
    usage_data = {
        '料金表番号': [1]*50 + [2]*30 + [3]*20,
        '使用量': np.random.uniform(5, 60, 100).tolist()
    }
    return pd.DataFrame(master_data), pd.DataFrame(usage_data)

# --- サイドバー構成 ---
with st.sidebar:
    st.markdown("""
        <h1 style="font-size: 2.2rem; margin-bottom: 0;">
            <span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 
            <span style="color:#2c3e50">Cluster</span>
        </h1>
        """, unsafe_allow_html=True)
    st.caption("AI料金集約エンジン")
    st.divider()
    
    st.header("📂 データ入力")
    file_master = st.file_uploader("① 料金表マスタ(CSV)", type='csv')
    file_usage = st.file_uploader("② 実績データ(CSV)", type='csv')
    
    st.divider()
    st.header("⚙️ 解析パラメーター")
    k = st.slider("統合後の目標グループ数", 2, 10, 3)
    low_usage_threshold = st.slider("低使用量層の定義 (m3)", 5, 40, 10, step=5)

# --- データ読み込みロジック ---
# ファイルが2つとも上がっていればそれを使う。そうでなければデモデータを使う。
if file_master and file_usage:
    df_m = pd.read_csv(file_master)
    df_u = pd.read_csv(file_usage)
    st.toast("✅ アップロードされたデータを解析中...")
else:
    df_m, df_u = get_demo_data()
    st.info("💡 現在はデモデータを表示しています。CSVをアップロードすると自動で切り替わります。")

# --- 解析エンジン本体 (ロジックは不変) ---
# 1. 列名調整
df_u = df_u.rename(columns={'使用量': '使用量_u', '料金表番号': '料金表番号_u'})
df_m = df_m.rename(columns={'料金プランID': '料金表番号_m'})

# 2. 高速金額計算
merged = pd.merge(df_u, df_m, left_on='料金表番号_u', right_on='料金表番号_m', how='left')
df_calc = merged[(merged['使用量_u'] >= merged['下限']) & (merged['使用量_u'] <= merged['上限'])].copy()
df_calc['当月金額'] = df_calc['基本料金'] + (df_calc['使用量_u'] * df_calc['従量単価'])

# 各プランの「一番低い区画の基本料金」を取得
base_fees = df_m.sort_values(['料金表番号_m', '下限']).groupby('料金表番号_m').head(1)[['料金表番号_m', '基本料金']]
base_fees.columns = ['料金表番号_m', 'マスタ基本料金']

# 3. 特徴量抽出
def calc_low_ratio(x):
    active = (x > 0).sum()
    return ((x > 0) & (x <= low_usage_threshold)).sum() / active if active > 0 else 0

df_features = df_calc.groupby(['料金表番号_u', '料金プラン名']).agg({
    '使用量_u': ['mean', calc_low_ratio],
    '当月金額': 'mean'
}).reset_index()

df_features.columns = ['料金表番号', '料金プラン名', '平均使用量(m3)', '低使用量層の割合', '平均金額']
df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)'].replace(0, 1)

# マスタの基本料金を紐付け
df_features = pd.merge(df_features, base_fees, left_on='料金表番号', right_on='料金表番号_m', how='left')

# --- AIクラスタリング ---
features = ['平均使用量(m3)', '低使用量層の割合', '実質単価(円/m3)']
X = df_features[features].fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

kmeans = KMeans(n_clusters=k, n_init='auto', random_state=42)
cluster_labels = kmeans.fit_predict(X_scaled)

df_features['新グループ'] = [chr(65 + i) for i in cluster_labels]
df_features = df_features.sort_values('新グループ')

# --- 可視化：3Dマップ ---
st.subheader("AI解析（3Dクラスタリング）")
sorted_groups = sorted(df_features['新グループ'].unique())

fig = px.scatter_3d(
    df_features, x='平均使用量(m3)', y='低使用量層の割合', z='実質単価(円/m3)',
    color='新グループ', 
    hover_name='料金プラン名',
    category_orders={"新グループ": sorted_groups},
    color_discrete_sequence=px.colors.qualitative.Pastel,
    height=700
)
fig.update_layout(margin=dict(l=0, r=0, b=0, t=0))
st.plotly_chart(fig, use_container_width=True)

# --- 集計：AI集約提案 ---
st.subheader("AI集約提案")
summary = df_features.groupby('新グループ').agg({
    '料金プラン名': lambda x: ' / '.join(x.astype(str)),
    '平均使用量(m3)': 'mean',
    '実質単価(円/m3)': 'mean',
    '平均金額': 'mean',
    'マスタ基本料金': 'mean'
}).reset_index()

summary['新基本料金案'] = summary['マスタ基本料金']
summary['新従量単価案'] = (summary['平均金額'] - summary['新基本料金案']) / summary['平均使用量(m3)'].replace(0, 1)

disp_summary = summary.drop(columns=['平均金額', 'マスタ基本料金']).rename(columns={'料金プラン名': '統合対象の現行プラン'})

st.table(disp_summary.style.format({
    '平均使用量(m3)': '{:,.1f}', '実質単価(円/m3)': '{:,.1f}',
    '新基本料金案': '{:,.0f}', '新従量単価案': '{:,.2f}'
}).set_properties(**{'text-align': 'right'}, subset=['平均使用量(m3)', '実質単価(円/m3)', '新基本料金案', '新従量単価案']))

# --- エクスポート ---
with st.sidebar:
    st.divider()
    csv_data = disp_summary.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(label="📥 提案書(CSV)を出力", data=csv_data, file_name="gasio_ai_proposal.csv", use_container_width=True)

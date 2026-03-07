import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px
import io

st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

# --- 1. インポート支援関数 ---
def get_cluster_sample_csv(type='master'):
    if type == 'master':
        df = pd.DataFrame({
            '料金プランID': [1, 1, 2, 2],
            '料金プラン名': ['一般A', '一般A', '暖房B', '暖房B'],
            '下限': [0, 20.1, 0, 30.1],
            '上限': [20.0, 9999, 30.0, 9999],
            '基本料金': [1000, 1400, 2000, 2500],
            '従量単価': [250, 230, 180, 160]
        })
    else:
        df = pd.DataFrame({
            '料金表番号': [1, 1, 2, 2, 1],
            '使用量': [15.5, 22.0, 45.0, 12.0, 8.5]
        })
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    return csv_buffer.getvalue()

def load_clean_csv(file):
    try:
        df = pd.read_csv(file, encoding='utf-8-sig')
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('￥', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
        return None

# --- デモデータ生成関数 ---
def get_demo_data():
    plan_names = ['一般Aプラン', 'ゆったりBプラン', '暖房Cプラン', '厨房特約D', 'エコジョーズE', '店舗用F', '大口工業用G', '福祉割引H', '高効率給湯器I', '夏期集中J']
    master_rows = []
    usage_rows = []
    np.random.seed(42)
    for i, name in enumerate(plan_names):
        plan_id = i + 1
        avg_usage = np.random.choice([12, 28, 55, 150]) 
        if avg_usage < 20:
            base_f = np.random.randint(800, 1200)
            unit_p = np.random.randint(220, 260)
        elif avg_usage < 40:
            base_f = np.random.randint(1300, 1800)
            unit_p = np.random.randint(180, 210)
        else:
            base_f = np.random.randint(2000, 3500)
            unit_p = np.random.randint(130, 170)
        master_rows.append([plan_id, name, 0, 20.0, base_f, unit_p])
        master_rows.append([plan_id, name, 20.1, 9999, base_f + 400, unit_p - 15])
        samples = np.random.normal(avg_usage, avg_usage * 0.4, 25).clip(1, 400)
        for val in samples:
            usage_rows.append([plan_id, val])
    df_m = pd.DataFrame(master_rows, columns=['料金プランID', '料金プラン名', '下限', '上限', '基本料金', '従量単価'])
    df_u = pd.DataFrame(usage_rows, columns=['料金表番号', '使用量'])
    return df_m, df_u

# --- サイドバー構成 ---
with st.sidebar:
    st.markdown("""<h1 style="font-size: 2.5rem; margin-bottom: 0;"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> <span style="color:#2c3e50">Cluster</span></h1>""", unsafe_allow_html=True)
    st.caption("AI料金集約エンジン")
    st.divider()
    
    st.header("⚙️ 解析パラメーター")
    k = st.slider("統合後の目標グループ数", 2, 10, 4)
    low_usage_threshold = st.slider("設備利用率の閾値 (m3)", 5, 40, 10, step=5)
    
    st.divider()
    st.header("📤 アウトプット")
    export_container = st.empty() 
    
    st.divider()
    st.header("📂 データ入力")
    with st.expander("ℹ️ インポートガイダンス"):
        st.download_button("📥 マスタ見本", get_cluster_sample_csv('master'), "sample_master.csv", "text/csv")
        st.download_button("📥 実績見本", get_cluster_sample_csv('usage'), "sample_usage.csv", "text/csv")
    file_master = st.file_uploader("① 料金表マスタ(CSV)", type='csv', key="master")
    file_usage = st.file_uploader("② 実績データ(CSV)", type='csv', key="usage")

# --- データ読み込み ---
if file_master and file_usage:
    df_m = load_clean_csv(file_master)
    df_u = load_clean_csv(file_usage)
    if df_m is not None and df_u is not None:
        st.toast("✅ 解析を開始します...")
    else:
        st.stop()
else:
    df_m, df_u = get_demo_data()
    df_m['料金プランID'] = df_m['料金プランID'].astype(int)

# --- 解析ロジック ---
df_u_proc = df_u.rename(columns={'使用量': '使用量_u', '料金表番号': '料金表番号_u'})
df_m_proc = df_m.rename(columns={'料金プランID': '料金表番号_m'})
merged = pd.merge(df_u_proc, df_m_proc, left_on='料金表番号_u', right_on='料金表番号_m', how='left')
df_calc = merged[(merged['使用量_u'] >= merged['下限'].astype(float)) & (merged['使用量_u'] <= merged['上限'].astype(float))].copy()
df_calc['当月金額'] = df_calc['基本料金'] + (df_calc['使用量_u'] * df_calc['従量単価'])
base_fees = df_m_proc.sort_values(['料金表番号_m', '下限']).groupby('料金表番号_m').head(1)[['料金表番号_m', '基本料金']]
base_fees.columns = ['料金表番号_m', 'マスタ基本料金']

def calc_low_ratio(x):
    active = (x > 0).sum()
    return ((x > 0) & (x <= low_usage_threshold)).sum() / active if active > 0 else 0

df_features = df_calc.groupby(['料金表番号_u', '料金プラン名']).agg({'使用量_u': ['mean', calc_low_ratio], '当月金額': 'mean'}).reset_index()
df_features.columns = ['料金表番号', '料金プラン名', '平均使用量(m3)', 'tmp_ratio', '平均金額']
df_features['設備利用率'] = (1 - df_features['tmp_ratio']) * 100
df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)'].replace(0, 1)
df_features = pd.merge(df_features, base_fees, left_on='料金表番号', right_on='料金表番号_m', how='left')

X = df_features[['平均使用量(m3)', '設備利用率', '実質単価(円/m3)']].fillna(0)
X_scaled = StandardScaler().fit_transform(X)
kmeans = KMeans(n_clusters=min(k, len(df_features)), n_init='auto', random_state=42)
df_features['新グループ'] = [chr(65 + i) for i in kmeans.fit_predict(X_scaled)]

# --- 表示 ---
st.subheader("AI解析（3Dクラスタリング）")
fig = px.scatter_3d(df_features, x='平均使用量(m3)', y='設備利用率', z='実質単価(円/m3)', color='新グループ', hover_name='料金プラン名', height=750)
st.plotly_chart(fig, use_container_width=True)

st.subheader("AI集約提案")
summary = df_features.groupby('新グループ').agg({'料金プラン名': lambda x: ' / '.join(x.astype(str)), '平均使用量(m3)': 'mean', '実質単価(円/m3)': 'mean', '平均金額': 'mean', 'マスタ基本料金': 'mean'}).reset_index()
summary['新基本料金案'] = summary['マスタ基本料金']
summary['新従量単価案'] = (summary['平均金額'] - summary['新基本料金案']) / summary['平均使用量(m3)'].replace(0, 1)
disp_summary = summary.drop(columns=['平均金額', 'マスタ基本料金']).rename(columns={'料金プラン名': '統合対象の現行プラン'})
st.table(disp_summary.style.format({'平均使用量(m3)': '{:,.1f}', '実質単価(円/m3)': '{:,.1f}', '新基本料金案': '{:,.0f}', '新従量単価案': '{:,.2f}'}))

# --- エクスポート（逆流表示） ---
with export_container:
    csv_data = disp_summary.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(label="📥 提案書(CSV)を出力", data=csv_data, file_name="gasio_ai_proposal.csv", use_container_width=True, key="export_btn")

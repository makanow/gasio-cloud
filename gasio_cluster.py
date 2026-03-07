import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px
import io

st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

# --- デモデータ生成兼サンプルデータ生成関数 ---
def get_demo_data():
    plan_names = ['一般A', 'ゆったりB', '暖房C', '厨房D', 'エコE', '店舗F', '大口G', '福祉H', '高効率I', '夏期J']
    master_rows = []
    usage_rows = []
    np.random.seed(42)
    for i, name in enumerate(plan_names):
        plan_id = i + 1
        avg_usage = np.random.choice([12, 28, 55, 150]) 
        base_f = np.random.randint(800, 3500)
        unit_p = np.random.randint(130, 260)
        master_rows.append([plan_id, name, 0, 20.0, base_f, unit_p])
        master_rows.append([plan_id, name, 20.1, 9999, base_f + 400, unit_p - 15])
        samples = np.random.normal(avg_usage, avg_usage * 0.4, 25).clip(1, 400).round(1)
        for val in samples:
            usage_rows.append([plan_id, val])
    
    df_m = pd.DataFrame(master_rows, columns=['料金プランID', '料金プラン名', '下限', '上限', '基本料金', '従量単価'])
    df_u = pd.DataFrame(usage_rows, columns=['料金表番号', '使用量'])
    return df_m, df_u

# --- CSV読み込み関数（BOM/文字コード対策） ---
def safe_read_csv(file):
    try:
        # まずはBOM付きUTF-8として読み込み
        return pd.read_csv(file, encoding='utf-8-sig')
    except UnicodeDecodeError:
        # 失敗した場合は日本向けExcelの標準（Shift-JIS/CP932）でリトライ
        file.seek(0)
        return pd.read_csv(file, encoding='cp932')

# --- サイドバー構成 ---
with st.sidebar:
    st.markdown("""
        <h1 style="font-size: 2.5rem; margin-bottom: 0;">
            <span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 
            <span style="color:#2c3e50">Cluster</span>
        </h1>
        """, unsafe_allow_html=True)
    st.caption("AI料金集約エンジン")
    st.divider()
    
    # 解析パラメーター
    st.header("⚙️ 解析パラメーター")
    k = st.slider("統合後の目標グループ数", 2, 10, 4)
    low_usage_threshold = st.slider("設備利用率の閾値 (m3)", 5, 40, 10, step=5)
    
    st.divider()

    # データ入力セクション
    st.header("📂 データ入力")
    
    # サンプルダウンロード
    st.subheader("1. 形式の確認")
    sample_m, sample_u = get_demo_data()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("マスタ手本", sample_m.to_csv(index=False, encoding='utf-8-sig'), "sample_master.csv", "text/csv")
    with col2:
        st.download_button("実績手本", sample_u.to_csv(index=False, encoding='utf-8-sig'), "sample_usage.csv", "text/csv")
    
    st.subheader("2. ファイルアップロード")
    file_master = st.file_uploader("① 料金表マスタ", type='csv')
    file_usage = st.file_uploader("② 実績データ", type='csv')
    
    if not (file_master and file_usage):
        st.info("💡 ファイルをアップロードしない場合は、自動的にデモデータで解析を実行します。")

# --- データ読み込みロジック ---
if file_master and file_usage:
    df_m = safe_read_csv(file_master)
    df_u = safe_read_csv(file_usage)
    st.toast("✅ データを正常に読み込みました")
else:
    df_m, df_u = get_demo_data()

# --- (以下、解析ロジックは前回と同様だが、カラム名の不一致に備えたエラーハンドリングを追加可能) ---
try:
    # 前述のデータ加工・クラスタリング処理（省略なしで実装）
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

    df_features = df_calc.groupby(['料金表番号_u', '料金プラン名']).agg({
        '使用量_u': ['mean', calc_low_ratio],
        '当月金額': 'mean'
    }).reset_index()

    df_features.columns = ['料金表番号', '料金プラン名', '平均使用量(m3)', 'tmp_ratio', '平均金額']
    df_features['設備利用率'] = (1 - df_features['tmp_ratio']) * 100
    df_features['実質単価(円/m3)'] = df_features['平均金額'] / df_features['平均使用量(m3)'].replace(0, 1)
    df_features = pd.merge(df_features, base_fees, left_on='料金表番号', right_on='料金表番号_m', how='left')

    # AIクラスタリング
    features = ['平均使用量(m3)', '設備利用率', '実質単価(円/m3)']
    X = df_features[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=min(k, len(df_features)), n_init='auto', random_state=42)
    cluster_labels = kmeans.fit_predict(X_scaled)
    df_features['新グループ'] = [chr(65 + i) for i in cluster_labels]
    df_features = df_features.sort_values('新グループ')

    # --- メイン表示 ---
    st.subheader("AI解析（3Dクラスタリング）")
    fig = px.scatter_3d(df_features, x='平均使用量(m3)', y='設備利用率', z='実質単価(円/m3)',
                        color='新グループ', hover_name='料金プラン名',
                        color_discrete_sequence=px.colors.qualitative.Dark24, height=700)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("AI集約提案")
    summary = df_features.groupby('新グループ').agg({
        '料金プラン名': lambda x: ' / '.join(x.astype(str)),
        '平均使用量(m3)': 'mean',
        '設備利用率': 'mean',
        '実質単価(円/m3)': 'mean',
        '平均金額': 'mean',
        'マスタ基本料金': 'mean'
    }).reset_index()
    summary['新基本料金案'] = summary['マスタ基本料金']
    summary['新従量単価案'] = (summary['平均金額'] - summary['新基本料金案']) / summary['平均使用量(m3)'].replace(0, 1)
    disp_summary = summary.drop(columns=['平均金額', 'マスタ基本料金']).rename(columns={'料金プラン名': '統合対象の現行プラン'})
    
    st.table(disp_summary.style.format({'平均使用量(m3)': '{:,.1f}', '設備利用率': '{:,.1f}%', 
                                         '実質単価(円/m3)': '{:,.1f}', '新基本料金案': '{:,.0f}', '新従量単価案': '{:,.2f}'}))

except Exception as e:
    st.error(f"解析中にエラーが発生しました。データの形式（カラム名など）が正しいか確認してください。エラー詳細: {e}")

# エクスポート
with st.sidebar:
    st.divider()
    if 'disp_summary' in locals():
        st.download_button(label="📥 提案書(CSV)を出力", data=disp_summary.to_csv(index=False, encoding='utf-8-sig'), 
                           file_name="gasio_ai_proposal.csv", use_container_width=True)

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px
import io

# 1. ページ設定
st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

# 2. カスタムCSS
st.markdown("""
    <style>
    div.stDownloadButton > button {
        border-radius: 8px;
        height: 3.5em;
        margin-bottom: 10px;
        background-color: #f8f9fa;
        color: #2c3e50;
        border: 1px solid #d1d5db;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    div.stDownloadButton > button:hover {
        border-color: #3498db;
        color: #3498db;
        background-color: #ffffff;
    }
    .st-expander { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. 補助関数
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
    return pd.DataFrame(master_rows, columns=['料金プランID', '料金プラン名', '下限', '上限', '基本料金', '従量単価']), \
           pd.DataFrame(usage_rows, columns=['料金表番号', '使用量'])

def safe_read_csv(file):
    try:
        return pd.read_csv(file, encoding='utf-8-sig')
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, encoding='cp932')

# --- 4. サイドバー：インポートセクション（最上位） ---
with st.sidebar:
    st.markdown("""<h1 style='font-size: 2.5rem; margin-bottom: 0;'>
                <span style='color:#2c3e50'>Gas</span><span style='color:#e74c3c'>i</span><span style='color:#3498db'>o</span> 
                <span style='color:#2c3e50'>Cluster</span></h1>""", unsafe_allow_html=True)
    st.caption("AI料金集約エンジン")
    st.divider()

    # 1. データインポート（ここが一番上）
    st.header("📂 データインポート")
    with st.expander("CSVファイルを指定", expanded=True):
        st.subheader("サンプルを取得")
        sample_m, sample_u = get_demo_data()
        st.download_button("📋 料金表マスタ(CSV)", sample_m.to_csv(index=False, encoding='utf-8-sig'), "sample_master.csv", use_container_width=True)
        st.download_button("📊 実績データ(CSV)", sample_u.to_csv(index=False, encoding='utf-8-sig'), "sample_usage.csv", use_container_width=True)
        st.markdown("---")
        st.subheader("アップロード")
        file_master = st.file_uploader("料金表マスタ(CSV)", type='csv', key="up_m")
        file_usage = st.file_uploader("実績データ(CSV)", type='csv', key="up_u")

    # プレースホルダ（後から中身を入れる枠）
    config_placeholder = st.container()
    filter_placeholder = st.container()
    export_placeholder = st.empty()

# --- 5. データロードの確定 ---
if file_master and file_usage:
    df_m = safe_read_csv(file_master)
    df_u = safe_read_csv(file_usage)
else:
    df_m, df_u = get_demo_data()

# --- 6. サイドバー：動的要素の配置（ロード後の数値を利用） ---
all_plans_raw = sorted(df_m['料金プラン名'].unique())
n_plans_raw = len(all_plans_raw)

with config_placeholder:
    st.divider()
    st.header("⚙️ 解析パラメーター")
    k = st.slider(
        "統合後の目標グループ数", 
        min_value=2, 
        max_value=max(2, n_plans_raw), 
        value=min(4, n_plans_raw)
    )
    low_usage_threshold = st.slider("設備利用率の閾値 (m3)", 5, 40, 10, step=5)

with filter_placeholder:
    st.divider()
    st.header("🔍 解析対象の選択")
    selected_plans = st.multiselect(
        "解析に含めるプランを選択", 
        options=all_plans_raw, 
        default=all_plans_raw
    )
    if not (file_master and file_usage):
        st.info("💡 デモデータでシミュレーション中。")

# --- 7. メイン解析ロジック ---
try:
    if not selected_plans:
        st.warning("⚠️ 解析対象のプランを1つ以上選択してください。")
    else:
        # データフィルタ・計算・クラスタリング
        df_m_filtered = df_m[df_m['料金プラン名'].isin(selected_plans)]
        df_u_proc = df_u.rename(columns={'使用量': '使用量_u', '料金表番号': '料金表番号_u'})
        df_m_proc = df_m_filtered.rename(columns={'料金プランID': '料金表番号_m'})
        merged = pd.merge(df_u_proc, df_m_proc, left_on='料金表番号_u', right_on='料金表番号_m', how='inner')
        df_calc = merged[(merged['使用量_u'] >= merged['下限'].astype(float)) & (merged['使用量_u'] <= merged['上限'].astype(float))].copy()
        df_calc['当月金額'] = df_calc['基本料金'] + (df_calc['使用量_u'] * df_calc['従量単価'])
        base_fees = df_m_proc.sort_values(['料金表番号_m', '下限']).groupby('料金表番号_m').head(1)[['料金表番号_m', '基本料金']]
        base_fees.columns = ['料金表番号_m', 'マスタ基本料金']

        def calc_low_ratio(x):
            active = (x > 0).sum()
            return ((x > 0) & (x <= low_usage_threshold)).sum() / active if active > 0 else 0

        df_features = df_calc.groupby(['料金表番号_u', '料金プラン名']).agg({'使用量_u': ['mean', calc_low_ratio], '当月金額': 'mean'}).reset_index()
        df_features.columns = ['料金表番号', '料金プラン名', '平均使用量(m3)', 'tmp_ratio', '平均金額']
        df_features['設備利用率'] = ((1 - df_features['tmp_ratio']) * 100).round(1)
        df_features['実質単価(円/m3)'] = (df_features['平均金額'] / df_features['平均使用量(m3)'].replace(0, 1)).round(1)
        df_features['平均使用量(m3)'] = df_features['平均使用量(m3)'].round(1)
        df_features = pd.merge(df_features.drop(columns=['tmp_ratio']), base_fees, left_on='料金表番号', right_on='料金表番号_m', how='left')

        X = df_features[['平均使用量(m3)', '設備利用率', '実質単価(円/m3)']].fillna(0)
        X_scaled = StandardScaler().fit_transform(X)
        kmeans = KMeans(n_clusters=min(k, len(df_features)), n_init='auto', random_state=42)
        df_features['新グループ'] = [chr(65 + i) for i in kmeans.fit_predict(X_scaled)]
        df_features = df_features.sort_values('新グループ')

        # 描画：グラフ
        st.subheader("AI解析（3Dクラスタリング）")
        fig = px.scatter_3d(df_features, x='平均使用量(m3)', y='設備利用率', z='実質単価(円/m3)', color='新グループ', hover_name='料金プラン名', height=750)
        st.plotly_chart(fig, use_container_width=True)

        # 描画：提案テーブル
        st.subheader("AI集約提案")
        summary = df_features.groupby('新グループ').agg({'料金プラン名': lambda x: ' / '.join(x.astype(str)), '平均使用量(m3)': 'mean', '設備利用率': 'mean', '実質単価(円/m3)': 'mean', '平均金額': 'mean', 'マスタ基本料金': 'mean'}).reset_index()
        summary['新基本料金案'] = summary['マスタ基本料金'].round(0)
        summary['新従量単価案'] = ((summary['平均金額'] - summary['新基本料金案']) / summary['平均使用量(m3)'].replace(0, 1)).round(2)
        disp_summary = summary.drop(columns=['平均金額', 'マスタ基本料金']).rename(columns={'料金プラン名': '統合対象の現行プラン'})
        
        # 行番号(0,1,2)を消して「新グループ」を見出しに
        st.table(disp_summary.set_index('新グループ').style.format({
            '平均使用量(m3)': '{:,.1f}', '設備利用率': '{:,.1f}%', '実質単価(円/m3)': '{:,.1f}', 
            '新基本料金案': '{:,.0f}', '新従量単価案': '{:,.2f}'
        }))

        # サイドバー：最下部に出力ボタン
        with export_placeholder.container():
            st.divider()
            st.header("📤 解析結果の出力")
            csv_data = disp_summary.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(label="📥 提案書(CSV)を出力", data=csv_data, file_name="gasio_ai_proposal.csv", use_container_width=True, key="btn_export")

except Exception as e:
    st.error(f"解析エラーが発生しました: {e}")

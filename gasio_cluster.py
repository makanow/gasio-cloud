import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import plotly.express as px
import io

st.set_page_config(layout="wide", page_title="Gasio Cluster AI")

# --- カスタムCSSの注入（ボタンデザインの修正） ---
st.markdown("""
    <style>
    /* ダウンロードボタンのカスタマイズ */
    div.stDownloadButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #f0f2f6;
        color: #2c3e50;
        border: 1px solid #d1d5db;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    div.stDownloadButton > button:hover {
        border-color: #3498db;
        color: #3498db;
        background-color: #ffffff;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    /* エクスパンダー内の余白調整 */
    .st-expander {
        border: none !important;
        background-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- データ生成関数（数値丸め処理済み） ---
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
        # 実績値を小数点第1位に丸める
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
    
    st.header("⚙️ 解析パラメーター")
    k = st.slider("統合後の目標グループ数", 2, 10, 4)
    low_usage_threshold = st.slider("設備利用率の閾値 (m3)", 5, 40, 10, step=5)
    
    st.divider()

# --- インポートセクションの折りたたみ（st.expander） ---
    with st.expander("📂 データインポート", expanded=False):
        st.subheader("1. サンプルを取得")
        sample_m, sample_u = get_demo_data()
        
        # 横長ボタンを上下に配置（use_container_widthで横幅を合わせる）
        st.download_button(
            "📋 料金表マスタ手本 (CSV)", 
            sample_m.to_csv(index=False, encoding='utf-8-sig'), 
            "sample_master.csv",
            use_container_width=True
        )
        st.download_button(
            "📊 実績データ手本 (CSV)", 
            sample_u.to_csv(index=False, encoding='utf-8-sig'), 
            "sample_usage.csv",
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("2. アップロード")
        file_master = st.file_uploader("料金表マスタ(CSV)", type='csv')
        file_usage = st.file_uploader("実績データ(CSV)", type='csv')

    if not (file_master and file_usage):
        st.info("💡 現在はデモデータを使用中。解析を反映するにはファイルをアップロードしてください。")

# --- 以下、解析ロジック（前回の改良版を維持） ---
# (中略：df_m, df_u の読み込みとクラスタリング処理)
# ...

import st as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import json
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン (元の仕様を維持)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; overflow-wrap: break-word; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }

    [data-testid="stDataEditor"] div[data-testid="stTable"] td[aria-readonly="false"] {
        border-right: 5px solid #fdd835 !important;
        background-color: #fffde7 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> シミュレーター</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">料金改定シミュレーション</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ヘルパー関数 (元のロジックを維持)
# ---------------------------------------------------------
def get_bill(usage, base, tiers_df):
    """基本料金 + 単価 * 使用量"""
    if usage == 0: return base
    for idx, row in tiers_df.iterrows():
        if row['MIN'] <= usage <= row['MAX']:
            return base + (usage * row['単価'])
    return base + (usage * tiers_df.iloc[-1]['単価'])

def get_current_bill(usage, p_id, df_master):
    """現行マスターから計算"""
    tiers = df_master[df_master['料金表番号'].astype(str) == str(p_id)].sort_values('MIN')
    if tiers.empty: return 0
    for idx, row in tiers.iterrows():
        if row['MIN'] <= usage <= row['MAX']:
            return row['基本料金'] + (usage * row['単価'])
    return tiers.iloc[-1]['基本料金'] + (usage * tiers.iloc[-1]['単価'])

# ---------------------------------------------------------
# 3. サイドバー: データ読み込み (元のインターフェース)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Input")
    file_m = st.file_uploader("1. 料金表マスター(CSV)", type="csv", key="m1")
    file_u = st.file_uploader("2. 請求データ(CSV)", type="csv", key="u1")
    
    st.divider()
    st.header("⚙️ Simulation Settings")
    new_base = st.number_input("新料金: 基本料金(円)", value=1500)
    
    # 区画設定
    num_tiers = st.slider("新料金の区画数", 1, 5, 3)
    new_tiers_data = []
    for i in range(num_tiers):
        st.markdown(f"**区画 {i+1}**")
        c1, c2 = st.columns(2)
        limit = c1.number_input(f"上限(m3)", value=10.0*(i+1) if i<num_tiers-1 else 999.0, key=f"lim_{i}")
        price = c2.number_input(f"単価(円)", value=600-(i*50), key=f"prc_{i}")
        new_tiers_data.append({
            "MIN": 0 if i==0 else new_tiers_data[i-1]["MAX"] + 0.1,
            "MAX": limit,
            "単価": price
        })
    df_new_tiers = pd.DataFrame(new_tiers_data)

# ---------------------------------------------------------
# 4. メイン表示 (元の仕様を維持)
# ---------------------------------------------------------
if file_m and file_u:
    df_master = pd.read_csv(file_m)
    df_usage = pd.read_csv(file_u)

    # 計算実行
    df_usage['現行料金'] = df_usage.apply(lambda x: get_current_bill(x['使用量'], x['料金表番号'], df_master), axis=1)
    df_usage['新料金'] = df_usage.apply(lambda x: get_bill(x['使用量'], new_base, df_new_tiers), axis=1)
    df_usage['差額'] = df_usage['新料金'] - df_usage['現行料金']

    # 指標表示
    m1, m2, m3 = st.columns(3)
    cur_sum = df_usage['現行料金'].sum()
    new_sum = df_usage['新料金'].sum()
    m1.metric("現行 収益合計", f"¥{cur_sum:,.0f}")
    m2.metric("新料金 収益合計", f"¥{new_sum:,.0f}", f"{new_sum-cur_sum:+,.0f}")
    m3.metric("増減率", f"{(new_sum/cur_sum-1)*100:+.1f}%")

    # グラフ
    st.divider()
    fig = px.histogram(df_usage, x="使用量", title="使用量分布", color_discrete_sequence=['#3498db'])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 計算結果サンプル (先頭100件)")
    st.dataframe(df_usage.head(100), use_container_width=True)

else:
    st.info("サイドバーからCSVファイルをアップロードしてください。")

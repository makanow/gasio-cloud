import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Gasio mini: Reset", layout="wide")
st.title("🔥 Gasio mini: 安定版リセット")

# 1. シンプルな読み込み
def smart_load(file):
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return df
        except: continue
    return None

# 2. 判定ロジック
def get_tier(usage, master):
    # MAX列で判定するだけの極めてシンプルなロジック
    applicable = master[master['MAX'] >= usage]
    if applicable.empty: return master.iloc[-1].name
    return applicable.iloc[0].name

# 3. メイン
file_u = st.sidebar.file_uploader("使用量CSV", type=['csv'])
file_m = st.sidebar.file_uploader("マスタCSV", type=['csv'])

if file_u and file_m:
    df_u = smart_load(file_u)
    df_m = smart_load(file_m)
    
    if df_u is not None and df_m is not None:
        # ID選択
        ids = sorted(df_u['料金表番号'].unique())
        target_id = st.selectbox("分析するID", ids)
        
        # 抽出
        df_target = df_u[df_u['料金表番号'] == target_id].copy()
        master_target = df_m[df_m['料金表番号'] == target_id].sort_values('MAX')
        
        # 判定
        df_target['Tier'] = df_target['使用量'].apply(lambda x: get_tier(x, master_target))
        
        # 集計
        agg = df_target.groupby('Tier').agg({'調定数': 'sum', '使用量': 'sum'}).reset_index()
        
        # グラフ
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(agg, values='調定数', names='Tier', title="調定数シェア"), use_container_width=True)
        c2.plotly_chart(px.pie(agg, values='使用量', names='Tier', title="使用量シェア"), use_container_width=True)
        st.table(agg)

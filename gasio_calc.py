import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio 電卓", page_icon="🧮", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; text-align: left; margin-bottom: 0; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; text-align: left; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; margin-bottom: 20px;}
    .stNumberInput input { font-weight: bold; color: #2c3e50; background-color: #fff; border: 2px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 電卓</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Rate Design Solver (Unified Logic Mode)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義 (Gasio mini から完全移植)
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX', 'max': 'MAX',
        'ID': '料金表番号', 'Code': '料金表番号'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if 'MAX' in df.columns: df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999)
    return df

def smart_load(file):
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

# ---------------------------------------------------------
# 3. 計算エンジン
# ---------------------------------------------------------
def solve_base(df_calc, base_a):
    df = df_calc.sort_values('No').reset_index(drop=True)
    results = {df.iloc[0]['No']: base_a}
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        # base_curr = base_prev + (unit_prev - unit_curr) * limit_prev
        res = results[prev['No']] + (prev['単位料金'] - curr['単位料金']) * prev['MAX']
        results[curr['No']] = res
    return results

def solve_unit(df_calc, base_a, unit_a):
    df = df_calc.sort_values('No').reset_index(drop=True)
    units = {df.iloc[0]['No']: unit_a}
    base_map = {df.iloc[0]['No']: base_a}
    for i in range(1, len(df)): base_map[df.iloc[i]['No']] = df.iloc[i]['基本料金(目標)']
    
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        # unit_curr = unit_prev - (base_curr - base_prev) / limit_prev
        res = units[prev['No']] - (base_map[curr['No']] - base_map[prev['No']]) / prev['MAX']
        units[curr['No']] = res
    return units

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_master = st.file_uploader("料金表マスタCSV (定義)", type=['csv'])

if file_master:
    df_master = smart_load(file_master)
    
    if df_master is not None:
        master_ids = sorted(df_master['料金表番号'].unique())
        selected_ids = st.multiselect("統合分析するIDを選択", master_ids, default=master_ids[:1])
        
        if not selected_ids:
            st.stop()

        # --- 【mini同等】構造チェック (上限の揺らぎを吸収) ---
        structure_check = {}
        for tid in selected_ids:
            m_sub = df_master[df_master['料金表番号'] == tid]
            if not m_sub.empty:
                fps = sorted(m_sub['MAX'].unique())
                if fps: fps[-1] = 999999999 # 指紋の末尾を固定
                structure_check[tid] = tuple(fps)
        
        if len(set(structure_check.values())) > 1:
            st.error("⚠️ 境界線が一致しません。統合計算不可。")
            st.stop()

        # --- 統合テンプレート作成 ---
        master_rep = df_master[df_master['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
        
        # UI表示用の初期データ
        init_data = pd.DataFrame({
            'No': range(1, len(master_rep)+1),
            '区画名': master_rep.get('区画名', [f"Tier {i+1}" for i in range(len(master_rep))]),
            'MAX': master_rep['MAX'],
            '基本': [0.0]*len(master_rep),
            '単位': [0.0]*len(master_rep)
        })

        tab1, tab2 = st.tabs(["🔄 単位料金から逆算", "🧮 基本料金から逆算"])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                b_a = st.number_input("第1区画 基本料金", value=1500.0, step=100.0, key="b1")
                edit_f = st.data_editor(init_data[['No', '区画名', 'MAX', '単位']].rename(columns={'単位': '単位料金(入力)'}), use_container_width=True)
            with c2:
                if not edit_f.empty:
                    df_run = edit_f.copy().sort_values('No')
                    df_run['MAX'] = pd.to_numeric(df_run['MAX']).fillna(999999999)
                    res_b = solve_base(df_run.rename(columns={'単位料金(入力)': '単位料金'}), b_a)
                    df_run['基本料金(算出)'] = df_run['No'].map(res_b)
                    st.dataframe(df_run[['No', '区画名', 'MAX', '基本料金(算出)', '単位料金(入力)']].style.format({"基本料金(算出)": "{:,.0f}", "単位料金(入力)": "{:,.2f}"}))

        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                b_a2 = st.number_input("第1区画 基本料金", value=1500.0, step=100.0, key="b2")
                u_a2 = st.number_input("第1区画 単位料金", value=500.0, step=10.0, key="u2")
                edit_r = st.data_editor(init_data[['No', '区画名', 'MAX', '基本']].rename(columns={'基本': '基本料金(目標)'}), use_container_width=True)
            with c2:
                if not edit_r.empty:
                    df_run2 = edit_r.copy().sort_values('No')
                    df_run2['MAX'] = pd.to_numeric(df_run2['MAX']).fillna(999999999)
                    res_u = solve_unit(df_run2.rename(columns={'基本料金(目標)': '基本料金(入力)'}), b_a2, u_a2)
                    df_run2['単位料金(算出)'] = df_run2['No'].map(res_u)
                    st.dataframe(df_run2[['No', '区画名', 'MAX', '基本料金(目標)', '単位料金(算出)']].style.format({"単位料金(算出)": "{:,.2f}"}))
else:
    st.info("👈 料金表マスタCSVを読み込んでください。")

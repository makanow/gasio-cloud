import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio 電卓", page_icon="🧮", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Gasio 電卓</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Unified Multi-Tariff Solver</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ロジック (指紋判定 & 統合)
# ---------------------------------------------------------
def normalize_master(df):
    rename_map = {'基本': '基本料金', '上限': 'MAX', '適用上限': 'MAX', '単位': '単位料金', '単価': '単位料金', 'ID': '料金表番号'}
    df = df.rename(columns=rename_map)
    for col in ['MAX', '料金表番号']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(999999999)
    return df

def get_structure_fingerprint(df_m, ids):
    structure_check = {}
    for tid in ids:
        m_sub = df_m[df_m['料金表番号'] == tid].sort_values('MAX')
        if not m_sub.empty:
            fps = sorted(m_sub['MAX'].unique())
            if fps: fps[-1] = 999999999 # 上限揺らぎ吸収
            structure_check[tid] = tuple(fps)
    return structure_check

# ---------------------------------------------------------
# 3. メイン
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Master Data")
    file_master = st.file_uploader("料金表マスタCSV", type=['csv'])

if file_master:
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file_master.seek(0)
            df_raw = pd.read_csv(file_master, encoding=enc)
            df_master = normalize_master(df_raw)
            break
        except: continue
    
    all_ids = sorted(df_master['料金表番号'].unique())
    selected_ids = st.multiselect("統合分析する料金表を選択 (10, 20など)", all_ids, default=all_ids[:1])

    if selected_ids:
        # 指紋判定
        fingerprints = get_structure_fingerprint(df_master, selected_ids)
        if len(set(fingerprints.values())) > 1:
            st.error("⚠️ 境界線が不一致な料金表が含まれています。合算表示できません。")
            st.stop()
        
        # 共通構造の抽出 (最初のIDをテンプレートにする)
        m_template = df_master[df_master['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
        m_template['MAX'] = pd.to_numeric(m_template['MAX'], errors='coerce').fillna(999999999)
        
        st.success(f"✅ ID {selected_ids} は同一構造です。統合シミュレーションを開始します。")

        # --- 計算用UIデータ ---
        if 'calc_df' not in st.session_state:
            st.session_state.calc_df = pd.DataFrame({
                'No': range(1, len(m_template)+1),
                '区画': m_template.get('区画名', [f"Tier {i+1}" for i in range(len(m_template))]),
                '境界': m_template['MAX'],
                '基本': [0.0]*len(m_template),
                '単位': [0.0]*len(m_template)
            })

        tab1, tab2 = st.tabs(["🔄 単位料金から逆算", "🧮 基本料金から逆算"])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                b_a = st.number_input("第1区画 基本料金", value=1500.0, step=100.0, key="b1")
                # 単位料金を入力するエディタ
                edit_fwd = st.data_editor(st.session_state.calc_df[['No', '区画', '境界', '単位']].rename(columns={'単位': '単位料金(入力)'}), use_container_width=True)
            with c2:
                # 逆算ロジック (統合表示)
                if not edit_fwd.empty:
                    df_run = edit_fwd.copy().sort_values('No')
                    df_run.iloc[-1, df_run.columns.get_loc('境界')] = 999999999
                    
                    # 逆算実行
                    res_bases = {df_run.iloc[0]['No']: b_a}
                    for i in range(1, len(df_run)):
                        p, c = df_run.iloc[i-1], df_run.iloc[i]
                        res_bases[c['No']] = res_bases[p['No']] + (p['単位料金(入力)'] - c['単位料金(入力)']) * p['境界']
                    
                    df_run['基本料金(算出)'] = df_run['No'].map(res_bases)
                    st.markdown("##### 統合計算結果")
                    st.dataframe(df_run[['No', '区画', '境界', '基本料金(算出)', '単位料金(入力)']].style.format({"境界": "{:,.0f}", "基本料金(算出)": "{:,.1f}", "単位料金(入力)": "{:,.2f}"}), hide_index=True, use_container_width=True)

        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                b_a2 = st.number_input("第1区画 基本料金", value=1500.0, step=100.0, key="b2")
                u_a2 = st.number_input("第1区画 単位料金", value=500.0, step=10.0, key="u2")
                edit_rev = st.data_editor(st.session_state.calc_df[['No', '区画', '境界', '基本']].rename(columns={'基本': '基本料金(目標)'}), use_container_width=True)
            with c2:
                if not edit_rev.empty:
                    df_run2 = edit_rev.copy().sort_values('No')
                    df_run2.iloc[-1, df_run2.columns.get_loc('境界')] = 999999999
                    
                    res_units = {df_run2.iloc[0]['No']: u_a2}
                    base_map = {df_run2.iloc[0]['No']: b_a2}
                    for i in range(1, len(df_run2)): base_map[df_run2.iloc[i]['No']] = df_run2.iloc[i]['基本料金(目標)']
                    
                    for i in range(1, len(df_run2)):
                        p, c = df_run2.iloc[i-1], df_run2.iloc[i]
                        res_units[c['No']] = res_units[p['No']] - (base_map[c['No']] - base_map[p['No']]) / p['境界']
                    
                    df_run2['単位料金(算出)'] = df_run2['No'].map(res_units)
                    df_run2['基本料金'] = df_run2['No'].map(base_map)
                    st.markdown("##### 統合計算結果")
                    st.dataframe(df_run2[['No', '区画', '境界', '基本料金', '単位料金(算出)']].style.format({"境界": "{:,.0f}", "基本料金": "{:,.1f}", "単位料金(算出)": "{:,.2f}"}), hide_index=True, use_container_width=True)

else:
    st.info("👈 料金表マスタを読み込んでください。")

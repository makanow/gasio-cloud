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
    .stNumberInput input { font-weight: bold; color: #2c3e50; background-color: #fff; border: 2px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Gasio 電卓</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Robust Multi-Tariff Design Solver</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義 (Gasio miniのロジックを完全移植)
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '上限': 'MAX', '下限': 'MIN', 'ID': '料金表番号',
        '適用上限': 'MAX', '単位': '単位料金', '単価': '単位料金'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
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

def get_structure_fingerprint(df_m, ids):
    """Miniと同等の指紋判定ロジック（上限揺らぎ吸収）"""
    structure_check = {}
    for tid in ids:
        m_sub = df_m[df_m['料金表番号'] == tid]
        if not m_sub.empty:
            fps = sorted(pd.to_numeric(m_sub['MAX'], errors='coerce').fillna(999999999).unique())
            if fps:
                fps[-1] = 999999999 # 上限を固定
            structure_check[tid] = tuple(fps)
    return structure_check

# ---------------------------------------------------------
# 3. 計算エンジン
# ---------------------------------------------------------
def solve_base(df_calc, base_a):
    df = df_calc.sort_values('No').reset_index(drop=True)
    results = {df.iloc[0]['No']: base_a}
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        limit_prev = prev['MAX']
        # 算式: base_curr = base_prev + (unit_prev - unit_curr) * limit_prev
        res = results[prev['No']] + (prev['単位料金'] - curr['単位料金']) * limit_prev
        results[curr['No']] = res
    return results

def solve_unit(df_calc, base_a, unit_a):
    df = df_calc.sort_values('No').reset_index(drop=True)
    units = {df.iloc[0]['No']: unit_a}
    bases = {df.iloc[0]['No']: base_a}
    for i in range(1, len(df)):
        bases[df.iloc[i]['No']] = df.iloc[i]['基本料金(入力)']
    
    for i in range(1, len(df)):
        prev, curr = df.iloc[i-1], df.iloc[i]
        limit_prev = prev['MAX']
        # 算式: unit_curr = unit_prev - (base_curr - base_prev) / limit_prev
        res = units[prev['No']] - (bases[curr['No']] - bases[prev['No']]) / limit_prev
        units[curr['No']] = res
    return units

# ---------------------------------------------------------
# 4. メイン UI
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Master Import")
    file_master = st.file_uploader("料金表マスタCSVを読み込む", type=['csv'])

if file_master:
    df_master = smart_load(file_master)
    if df_master is not None:
        all_ids = sorted(df_master['料金表番号'].unique())
        selected_ids = st.multiselect("シミュレートする料金表番号を選択", all_ids, default=all_ids[:1])

        if selected_ids:
            # 構造チェック (指紋判定)
            structure_map = get_structure_fingerprint(df_master, selected_ids)
            if len(set(structure_map.values())) > 1:
                st.error("⚠️ 選択した料金表間で境界線が一致しません。合算シミュレーション不可。")
                st.stop()
            
            # 代表構造を取得
            rep_id = selected_ids[0]
            m_rep = df_master[df_master['料金表番号'] == rep_id].sort_values('MAX').reset_index(drop=True)
            # MAXを数値化して保持
            m_rep['MAX'] = pd.to_numeric(m_rep['MAX'], errors='coerce').fillna(999999999)
            
            # --- 初期データ作成 ---
            initial_data = pd.DataFrame({
                'No': range(1, len(m_rep)+1),
                '区画名': m_rep.get('区画名', [f"Tier {i+1}" for i in range(len(m_rep))]),
                'MAX': m_rep['MAX'],
                '基本料金(入力)': [0.0]*len(m_rep),
                '単位料金(入力)': [0.0]*len(m_rep)
            })

            tab1, tab2 = st.tabs(["🔄 従量料金基準で基本を算出", "🧮 基本料金基準で単位を算出"])

            with tab1:
                col_in, col_res = st.columns(2)
                with col_in:
                    base_a = st.number_input("A区画 基本料金", value=1500.0, step=100.0, key="b1")
                    # MAXは表示するが、最後の行は自動で999,999,999扱い
                    edit_fwd = st.data_editor(initial_data[['No', '区画名', 'MAX', '単位料金(入力)']], key="e1", use_container_width=True)
                with col_res:
                    if not edit_fwd.empty:
                        calc_df = edit_fwd.rename(columns={'単位料金(入力)': '単位料金'})
                        # 最後のMAXを強制固定
                        calc_df.iloc[-1, calc_df.columns.get_loc('MAX')] = 999999999
                        res_bases = solve_base(calc_df, base_a)
                        calc_df['基本料金(算出)'] = calc_df['No'].map(res_bases)
                        st.dataframe(calc_df[['No', '区画名', 'MAX', '基本料金(算出)', '単位料金']].style.format({"基本料金(算出)": "{:,.0f}", "単位料金": "{:,.2f}"}))

            with tab2:
                col_in2, col_res2 = st.columns(2)
                with col_in2:
                    base_a2 = st.number_input("A区画 基本料金", value=1500.0, step=100.0, key="b2")
                    unit_a2 = st.number_input("A区画 単位料金", value=500.0, step=10.0, key="u2")
                    edit_rev = st.data_editor(initial_data[['No', '区画名', 'MAX', '基本料金(入力)']], key="e2", use_container_width=True)
                with col_res2:
                    if not edit_rev.empty:
                        calc_df2 = edit_rev.copy()
                        calc_df2.iloc[-1, calc_df2.columns.get_loc('MAX')] = 999999999
                        res_units = solve_unit(calc_df2, base_a2, unit_a2)
                        calc_df2['単位料金(算出)'] = calc_df2['No'].map(res_units)
                        st.dataframe(calc_df2[['No', '区画名', 'MAX', '基本料金(入力)', '単位料金(算出)']].style.format({"単位料金(算出)": "{:,.2f}"}))
else:
    st.info("👈 サイドバーから料金表マスタCSVをアップロードしてください。")

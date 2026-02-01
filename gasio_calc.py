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
st.markdown('<div class="sub-title">Rate Design Solver (Unified Mode)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ロジック（上限揺らぎ吸収 & 指紋判定）
# ---------------------------------------------------------
def normalize_master(df):
    rename_map = {'基本': '基本料金', '上限': 'MAX', '適用上限': 'MAX', '単位': '単位料金', '単価': '単位料金', 'ID': '料金表番号'}
    df = df.rename(columns=rename_map)
    # MAX列を数値化（99999...等の巨大数値も許容）
    if 'MAX' in df.columns:
        df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    if '料金表番号' in df.columns:
        df['料金表番号'] = pd.to_numeric(df['料金表番号'], errors='coerce').fillna(0)
    return df

def get_fingerprint(df_m, ids):
    """複数IDの境界線が一致するか判定する（最後の値は無視して比較）"""
    check_map = {}
    for tid in ids:
        m_sub = df_m[df_m['料金表番号'] == tid].sort_values('MAX')
        if not m_sub.empty:
            fps = sorted(m_sub['MAX'].unique())
            # 上限揺らぎ吸収：最後の値は強制的に共通の巨大数値へ
            if fps: fps[-1] = 999999999.0
            check_map[tid] = tuple(fps)
    return check_map

# ---------------------------------------------------------
# 3. 計算エンジン（初期コードのロジックを継承）
# ---------------------------------------------------------
def solve_base(df_calc, base_a):
    df = df_calc.sort_values('No').reset_index(drop=True)
    results = {df.iloc[0]['No']: base_a}
    for i in range(1, len(df)):
        p, c = df.iloc[i-1], df.iloc[i]
        # 接続点（上限値）で料金が一致する基本料金を算出
        res = results[p['No']] + (p['単位料金'] - c['単位料金']) * p['境界']
        results[c['No']] = res
    return results

def solve_unit(df_calc, base_a, unit_a):
    df = df_calc.sort_values('No').reset_index(drop=True)
    units = {df.iloc[0]['No']: unit_a}
    base_map = {df.iloc[0]['No']: base_a}
    for i in range(1, len(df)): base_map[df.iloc[i]['No']] = df.iloc[i]['基本料金(目標)']
    
    for i in range(1, len(df)):
        p, c = df.iloc[i-1], df.iloc[i]
        # 接続点での基本料金差を埋める単位料金を算出
        res = units[p['No']] - (base_map[c['No']] - base_map[p['No']]) / p['境界']
        units[c['No']] = res
    return units

# ---------------------------------------------------------
# 4. メイン UI
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_master = st.file_uploader("料金表マスタCSVを読み込む", type=['csv'])

if file_master:
    # エンコーディング対応
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file_master.seek(0)
            df_raw = pd.read_csv(file_master, encoding=enc)
            df_m = normalize_master(df_raw)
            break
        except: continue
    
    all_ids = sorted(df_m['料金表番号'].unique())
    selected_ids = st.multiselect("統合分析する料金表を選択 (例: 10, 20)", all_ids, default=all_ids[:1])

    if selected_ids:
        # 指紋チェック
        fingerprints = get_fingerprint(df_m, selected_ids)
        if len(set(fingerprints.values())) > 1:
            st.error("⚠️ 選択された料金表間で境界線が一致しません。個別に分析してください。")
            st.stop()
        
        # 統合テンプレート作成
        rep_id = selected_ids[0]
        m_rep = df_m[df_m['料金表番号'] == rep_id].sort_values('MAX').reset_index(drop=True)
        
        # セッション状態の初期化
        init_df = pd.DataFrame({
            'No': range(1, len(m_rep)+1),
            '区画': m_rep.get('区画名', [f"Tier {i+1}" for i in range(len(m_rep))]),
            '境界': m_rep['MAX'],
            '基本': [0.0]*len(m_rep),
            '単位': [0.0]*len(m_rep)
        })

        tab1, tab2 = st.tabs(["🔄 単位料金から基本を算出", "🧮 基本料金から単位を算出"])

        with tab1:
            st.info("💡 複数のIDを選択中でも、共通の区画構造として1つの表で計算します。")
            c1, c2 = st.columns(2)
            with c1:
                b_a = st.number_input("第1区画 基本料金", value=1500.0, step=100.0, key="b1")
                edit_f = st.data_editor(init_df[['No', '区画', '境界', '単位']].rename(columns={'単位': '単位料金(入力)'}), use_container_width=True)
            with c2:
                if not edit_f.empty:
                    df_run = edit_f.copy()
                    df_run.iloc[-1, df_run.columns.get_loc('境界')] = 999999999.0 # 上限固定
                    res = solve_base(df_run.rename(columns={'単位料金(入力)': '単位料金'}), b_a)
                    df_run['基本料金(算出)'] = df_run['No'].map(res)
                    st.dataframe(df_run[['No', '区画', '境界', '基本料金(算出)', '単位料金(入力)']].style.format({"境界": "{:,.0f}", "基本料金(算出)": "{:,.0f}", "単位料金(入力)": "{:,.2f}"}), hide_index=True)

        with tab2:
            st.info("💡 設定した基本料金のターゲットに合わせて、単位料金を自動計算します。")
            c1, c2 = st.columns(2)
            with c1:
                b_a2 = st.number_input("第1区画 基本料金", value=1500.0, step=100.0, key="b2")
                u_a2 = st.number_input("第1区画 単位料金", value=500.0, step=10.0, key="u2")
                edit_r = st.data_editor(init_df[['No', '区画', '境界', '基本']].rename(columns={'基本': '基本料金(目標)'}), use_container_width=True)
            with c2:
                if not edit_r.empty:
                    df_run2 = edit_r.copy()
                    df_run2.iloc[-1, df_run2.columns.get_loc('境界')] = 999999999.0 # 上限固定
                    res_u = solve_unit(df_run2.rename(columns={'基本料金(目標)': '基本料金(入力)'}), b_a2, u_a2)
                    df_run2['単位料金(算出)'] = df_run2['No'].map(res_u)
                    st.dataframe(df_run2[['No', '区画', '境界', '基本料金(目標)', '単位料金(算出)']].style.format({"境界": "{:,.0f}", "基本料金(目標)": "{:,.0f}", "単位料金(算出)": "{:,.2f}"}), hide_index=True)

else:
    st.info("👈 料金表マスタ(CSV)をサイドバーから読み込んでください。")

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
st.markdown('<div class="sub-title">Rate Design Solver (Fixed Auto-Indexing)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ロジック
# ---------------------------------------------------------

def get_alpha_label(n):
    """0 -> A, 1 -> B, 25 -> Z..."""
    label = ""
    while n >= 0:
        label = chr(n % 26 + 65) + label
        n = n // 26 - 1
    return label

def stabilize_dataframe(df):
    """再採番と上限固定のロジック"""
    if df.empty: return df
    df = df.reset_index(drop=True)
    df['No'] = df.index + 1
    df['区画名'] = [get_alpha_label(i) for i in range(len(df))]
    # 安全に最終行の上限を更新
    df.loc[df.index[-1], '適用上限(m3)'] = 99999.0
    return df

def solve_base(df_input, base_a):
    """基本料金の逆算ロジック"""
    df = df_input.copy().sort_values('No').reset_index(drop=True)
    if df.empty: return {}
    first_no = df.iloc[0]['No']
    bases = {first_no: base_a}
    for i in range(1, len(df)):
        prev_row, curr_row = df.iloc[i-1], df.iloc[i]
        # NoがNoneでないことを確認して計算
        p_no, c_no = prev_row['No'], curr_row['No']
        if pd.notnull(p_no) and pd.notnull(c_no):
            base_prev = bases.get(p_no, 0)
            base_curr = base_prev + (prev_row['単位料金'] - curr_row['単位料金']) * prev_row['適用上限(m3)']
            bases[c_no] = base_curr
    return bases

# ---------------------------------------------------------
# 3. UI & ステート管理
# ---------------------------------------------------------

if 'calc_data' not in st.session_state:
    initial_df = pd.DataFrame({
        'No': [1, 2, 3],
        '区画名': ['A', 'B', 'C'],
        '適用上限(m3)': [8.0, 30.0, 99999.0],
        '基本料金(入力)': [1500.0, 2300.0, 5300.0],
        '単位料金(入力)': [500.0, 400.0, 300.0]
    })
    st.session_state.calc_data = stabilize_dataframe(initial_df)

tab1, tab2 = st.tabs(["🔄 従量料金基準", "🧮 基本料金基準"])

with tab1:
    st.info("💡 行の追加・削除に合わせて No. と 区画名 が自動的にリセットされます。")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        # セッションから第1区画の基本料金を取得
        current_base_a = float(st.session_state.calc_data.iloc[0]['基本料金(入力)']) if not st.session_state.calc_data.empty else 1500.0
        base_a_fwd = st.number_input("✏️ 第1区画(A) 基本料金", value=current_base_a, step=10.0)
        
        cols_to_edit = ['No', '区画名', '適用上限(m3)', '単位料金(入力)']
        edited_fwd = st.data_editor(
            st.session_state.calc_data[cols_to_edit],
            column_config={
                "No": st.column_config.NumberColumn("🔒 No", disabled=True, width=50),
                "区画名": st.column_config.TextColumn("🔒 区画", disabled=True, width=70),
                "適用上限(m3)": st.column_config.NumberColumn("✏️ 適用上限", format="%.1f", required=True),
                "単位料金(入力)": st.column_config.NumberColumn("✏️ 単位料金", format="%.2f", required=True)
            },
            num_rows="dynamic", use_container_width=True, key="editor_fwd"
        )
        
        # 変更検知
        if not edited_fwd.equals(st.session_state.calc_data[cols_to_edit]):
            new_df = stabilize_dataframe(edited_fwd)
            # 他の列との整合性を維持
            new_master = new_df.copy()
            new_master = new_master.merge(st.session_state.calc_data[['No', '基本料金(入力)']], on='No', how='left').fillna(0.0)
            st.session_state.calc_data = new_master
            st.rerun()

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        if not st.session_state.calc_data.empty:
            calc_df = st.session_state.calc_data.copy().rename(columns={'単位料金(入力)': '単位料金'})
            res_bases = solve_base(calc_df, base_a_fwd)
            
            # 安全なリスト構築: Noが有効な数値である行のみ処理
            res_list = []
            for _, r in calc_df.iterrows():
                if pd.notnull(r['No']):
                    res_list.append({
                        "No": int(r['No']), 
                        "区画名": r['区画名'], 
                        "適用上限": r['適用上限(m3)'], 
                        "基本料金(算出)": res_bases.get(r['No'], 0), 
                        "単位料金": r['単位料金']
                    })
            
            if res_list:
                st.dataframe(pd.DataFrame(res_list).set_index('No'), use_container_width=True)

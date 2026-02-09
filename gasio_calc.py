import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Style)
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
st.markdown('<div class="sub-title">Rate Design Solver (Auto-Indexing Mode)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ロジック (自動採番・計算)
# ---------------------------------------------------------

def get_alpha_label(n):
    """0 -> A, 1 -> B, 25 -> Z, 26 -> AA..."""
    label = ""
    while n >= 0:
        label = chr(n % 26 + 65) + label
        n = n // 26 - 1
    return label

def stabilize_dataframe(df):
    """No・区画名の再採番と最終行上限の固定"""
    if df.empty: return df
    df = df.reset_index(drop=True)
    df['No'] = df.index + 1
    df['区画名'] = [get_alpha_label(i) for i in range(len(df))]
    df.loc[df.index[-1], '適用上限(m3)'] = 99999.0
    return df

def solve_base(df_input, base_a):
    df = df_input.copy().sort_values('No').reset_index(drop=True)
    if df.empty: return {}
    first_no = df.iloc[0]['No']
    bases = {first_no: base_a}
    for i in range(1, len(df)):
        prev_row, curr_row = df.iloc[i-1], df.iloc[i]
        base_prev = bases.get(prev_row['No'], 0)
        base_curr = base_prev + (prev_row['単位料金'] - curr_row['単位料金']) * prev_row['適用上限(m3)']
        bases[curr_row['No']] = base_curr
    return bases

# ---------------------------------------------------------
# 3. UI & ステート管理
# ---------------------------------------------------------

# 初期状態の構築
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
    st.info("💡 行を追加すると、Noと区画名は自動更新されます。最終行の上限は99999に固定されます。")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        base_a_fwd = st.number_input("✏️ 第1区画(A) 基本料金", value=float(st.session_state.calc_data.iloc[0]['基本料金(入力)']), step=10.0)
        
        # 編集対象の抽出
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
        
        # 変更の反映ロジック
        if not edited_fwd.equals(st.session_state.calc_data[cols_to_edit]):
            new_df = stabilize_dataframe(edited_fwd)
            # 基本料金(入力)をマージして保持
            new_master = new_df.merge(st.session_state.calc_data[['No', '基本料金(入力)']], on='No', how='left').fillna(0.0)
            st.session_state.calc_data = new_master
            st.rerun()

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        if not st.session_state.calc_data.empty:
            calc_df = st.session_state.calc_data.copy().rename(columns={'単位料金(入力)': '単位料金'})
            res_bases = solve_base(calc_df, base_a_fwd)
            res_list = [{"No": int(r['No']), "区画名": r['区画名'], "適用上限": r['適用上限(m3)'], 
                         "基本料金(算出)": res_bases.get(r['No'], 0), "単位料金": r['単位料金']} 
                        for _, r in calc_df.iterrows()]
            st.dataframe(pd.DataFrame(res_list).set_index('No'), use_container_width=True)

# (Tab 2はTab 1のロジックを応用して構築可能)

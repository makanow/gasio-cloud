import streamlit as st
import pandas as pd

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
st.markdown('<div class="sub-title">Rate Design Solver (Specification Compliant)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ロジック
# ---------------------------------------------------------

def get_alpha_label(n):
    label = ""
    while n >= 0:
        label = chr(n % 26 + 65) + label
        n = n // 26 - 1
    return label

def solve_base(df, base_a):
    if df.empty: return {}
    sorted_df = df.sort_values('No')
    first_no = sorted_df.iloc[0]['No']
    bases = {first_no: base_a}
    for i in range(1, len(sorted_df)):
        prev = sorted_df.iloc[i-1]
        curr = sorted_df.iloc[i]
        bases[curr['No']] = bases[prev['No']] + (prev['単位料金(入力)'] - curr['単位料金(入力)']) * prev['適用上限(m3)']
    return bases

def stabilize_dataframe(df, base_a):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=['No', '区画名', '適用上限(m3)', '単位料金(入力)', '基本料金(算出)'])
    
    df = df.reset_index(drop=True)
    df['No'] = range(1, len(df) + 1)
    df['区画名'] = [get_alpha_label(i) for i in range(len(df))]
    df['適用上限(m3)'] = pd.to_numeric(df['適用上限(m3)'], errors='coerce').fillna(0.0)
    df['単位料金(入力)'] = pd.to_numeric(df['単位料金(入力)'], errors='coerce').fillna(0.0)
    df.loc[df.index[-1], '適用上限(m3)'] = 99999.0
    
    res_bases = solve_base(df, base_a)
    df['基本料金(算出)'] = df['No'].map(res_bases)
    return df

# ---------------------------------------------------------
# 3. メイン UI
# ---------------------------------------------------------

if 'calc_data' not in st.session_state:
    init_df = pd.DataFrame([
        {'No': 1, '区画名': 'A', '適用上限(m3)': 8.0, '単位料金(入力)': 650.0},
        {'No': 2, '区画名': 'B', '適用上限(m3)': 30.0, '単位料金(入力)': 550.0},
        {'No': 3, '区画名': 'C', '適用上限(m3)': 99999.0, '単位料金(入力)': 450.0}
    ])
    st.session_state.calc_data = stabilize_dataframe(init_df, 1500.0)
    st.session_state.last_base_a = 1500.0

tab1, tab2 = st.tabs(["🔄 従量料金基準", "🧮 基本料金基準"])

with tab1:
    st.info("💡 操作ガイド: 行の追加/削除に連動して自動計算されます。空白行は表示されません。")
    c1, c2 = st.columns([1.1, 0.9])
    
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        base_a_fwd = st.number_input("✏️ 第1区画(A) 基本料金", value=float(st.session_state.last_base_a), step=10.0)
        
        edited_df = st.data_editor(
            st.session_state.calc_data,
            column_config={
                "No": st.column_config.NumberColumn("🔒 No", disabled=True, width=40),
                "区画名": st.column_config.TextColumn("🔒 区画", disabled=True, width=60),
                "適用上限(m3)": st.column_config.NumberColumn("✏️ 適用上限", format="%.1f"),
                "単位料金(入力)": st.column_config.NumberColumn("✏️ 単位料金", format="%.2f"),
                "基本料金(算出)": st.column_config.NumberColumn("📊 基本料金(自算)", disabled=True, format="%.2f") # 小数第2位指定
            },
            num_rows="dynamic",
            use_container_width=True,
            key="main_editor"
        )
        
        if base_a_fwd != st.session_state.last_base_a or not edited_df.equals(st.session_state.calc_data):
            st.session_state.last_base_a = base_a_fwd
            st.session_state.calc_data = stabilize_dataframe(edited_df, base_a_fwd)
            st.rerun()

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        display_df = st.session_state.calc_data.copy()
        
        # 指示通り、単位料金を基本料金の前に配置
        target_cols = ['区画名', '適用上限(m3)', '単位料金(入力)', '基本料金(算出)']
        available_cols = [c for c in target_cols if c in display_df.columns]
        
        if not display_df.empty:
            st.dataframe(
                display_df.set_index('No')[available_cols].style.format({
                    '適用上限(m3)': "{:,.1f}",
                    '単位料金(入力)': "{:,.2f}",
                    '基本料金(算出)': "{:,.2f}" # 小数第2位指定
                }, na_rep="-"), 
                use_container_width=True
            )

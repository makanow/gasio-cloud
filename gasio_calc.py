import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Calculator Style)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio 電卓", page_icon="🧮", layout="centered")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2c3e50; text-align: center; margin-bottom: 0; }
    .sub-title { font-size: 1.0rem; color: #7f8c8d; text-align: center; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; margin-bottom: 20px;}
    .stNumberInput input { font-weight: bold; color: #2c3e50; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 電卓</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Rate Design Solver</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 計算ロジック
# ---------------------------------------------------------

def solve_base(df_input, base_a):
    """
    順算: 従量料金(Unit)から基本料金(Base)を算出
    Base[n] = Base[n-1] + (Unit[n-1] - Unit[n]) * Limit[n-1]
    """
    df = df_input.copy().sort_values('No')
    bases = {1: base_a}
    
    # 計算
    for i in range(2, len(df) + 2):
        prev = df[df['No'] == i-1].iloc[0]
        curr = df[df['No'] == i].iloc[0]
        
        limit_prev = prev['適用上限(m3)']
        unit_prev = prev['単位料金']
        unit_curr = curr['単位料金']
        
        # スライド計算式
        bases[i] = bases[i-1] + (unit_prev - unit_curr) * limit_prev
        
    return bases

def solve_unit(df_input, base_a, unit_a):
    """
    逆算: 基本料金(Base)から従量料金(Unit)を算出
    変形: Unit[n] = Unit[n-1] - (Base[n] - Base[n-1]) / Limit[n-1]
    """
    df = df_input.copy().sort_values('No')
    units = {1: unit_a}
    
    # 入力された基本料金を辞書化
    bases = {1: base_a}
    for idx, row in df.iterrows():
        if row['No'] > 1:
            bases[row['No']] = row['基本料金(入力)']

    # 計算
    for i in range(2, len(df) + 2):
        prev_row = df[df['No'] == i-1].iloc[0]
        # curr_row = df[df['No'] == i].iloc[0] # currの基本料金はbasesにある
        
        limit_prev = prev_row['適用上限(m3)']
        base_prev = bases[i-1]
        base_curr = bases[i]
        unit_prev = units[i-1]
        
        # 逆算式
        # Base_diff = (Unit_prev - Unit_curr) * Limit
        # Unit_curr = Unit_prev - (Base_diff / Limit)
        if limit_prev > 0:
            units[i] = unit_prev - (base_curr - base_prev) / limit_prev
        else:
            units[i] = 0 # ゼロ除算回避
            
    return units

# ---------------------------------------------------------
# 3. UI
# ---------------------------------------------------------

# 初期データ
if 'calc_data' not in st.session_state:
    st.session_state.calc_data = pd.DataFrame({
        'No': [1, 2, 3],
        '区画名': ['A', 'B', 'C'],
        '適用上限(m3)': [20.0, 100.0, 99999.0],
        '基本料金(入力)': [1000.0, 1500.0, 2500.0], # 逆算用
        '単位料金(入力)': [150.0, 140.0, 130.0]     # 順算用
    })

tab1, tab2 = st.tabs(["🔄 順算 (Base求)", "🧮 逆算 (Unit求)"])

# === Tab 1: 順算モード ===
with tab1:
    st.subheader("単位料金 → 基本料金")
    st.caption("従量単価を決めて、基本料金を自動計算します")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        base_a_fwd = st.number_input("A区画 基本料金", value=1000.0, step=10.0, key="fwd_base_a")
        
        edited_fwd = st.data_editor(
            st.session_state.calc_data[['No', '区画名', '適用上限(m3)', '単位料金(入力)']],
            column_config={
                "No": st.column_config.NumberColumn(disabled=True, width=50),
                "適用上限(m3)": st.column_config.NumberColumn(format="%.1f"),
                "単位料金(入力)": st.column_config.NumberColumn(format="%.2f", label="単位料金")
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_fwd"
        )
        
    with c2:
        st.markdown("###### 📝 計算結果")
        if not edited_fwd.empty:
            # カラム名を統一して計算関数へ
            calc_df = edited_fwd.rename(columns={'単位料金(入力)': '単位料金'})
            res_bases = solve_base(calc_df, base_a_fwd)
            
            res_list = []
            for idx, row in calc_df.iterrows():
                no = row['No']
                res_list.append({
                    "区画": row['区画名'],
                    "基本料金 (算出)": res_bases.get(no, 0),
                    "単位料金": row['単位料金']
                })
            
            st.dataframe(pd.DataFrame(res_list).style.format({
                "基本料金 (算出)": "{:,.2f}", 
                "単位料金": "{:,.2f}"
            }), use_container_width=True)


# === Tab 2: 逆算モード ===
with tab2:
    st.subheader("基本料金 → 単位料金")
    st.caption("基本料金を先に決めて、整合する従量単価を逆算します")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        # 逆算には「A区画の基本料金」と「A区画の単位料金」の両方が起点として必要
        col_start1, col_start2 = st.columns(2)
        base_a_rev = col_start1.number_input("A区画 基本料金", value=1000.0, step=10.0, key="rev_base_a")
        unit_a_rev = col_start2.number_input("A区画 単位料金", value=150.00, step=1.0, key="rev_unit_a")

        edited_rev = st.data_editor(
            st.session_state.calc_data[['No', '区画名', '適用上限(m3)', '基本料金(入力)']],
            column_config={
                "No": st.column_config.NumberColumn(disabled=True, width=50),
                "適用上限(m3)": st.column_config.NumberColumn(format="%.1f"),
                "基本料金(入力)": st.column_config.NumberColumn(format="%.2f", label="基本料金(目標)")
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_rev"
        )

    with c2:
        st.markdown("###### 📝 計算結果")
        if not edited_rev.empty:
            res_units = solve_unit(edited_rev, base_a_rev, unit_a_rev)
            
            res_list = []
            # 入力データにはA区画の基本料金が含まれていない場合があるので統合
            # (DataEditorはNo1から持っている前提)
            for idx, row in edited_rev.iterrows():
                no = row['No']
                base_val = base_a_rev if no == 1 else row['基本料金(入力)']
                
                res_list.append({
                    "区画": row['区画名'],
                    "基本料金": base_val,
                    "単位料金 (算出)": res_units.get(no, 0)
                })
            
            st.dataframe(pd.DataFrame(res_list).style.format({
                "基本料金": "{:,.2f}", 
                "単位料金 (算出)": "{:,.4f}"
            }), use_container_width=True)
            
            st.info("💡 「単位料金」がマイナスになる場合は、基本料金の傾斜がきつすぎます。")
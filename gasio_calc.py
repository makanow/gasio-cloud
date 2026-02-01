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
    /* 入力フォームを目立たせる */
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 電卓</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Rate Design Solver</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 計算ロジック
# ---------------------------------------------------------
def solve_base(df_input, base_a):
    df = df_input.copy().sort_values('No').reset_index(drop=True)
    if df.empty: return {}
    
    first_no = df.iloc[0]['No']
    bases = {first_no: base_a}
    
    for i in range(1, len(df)):
        prev_row = df.iloc[i-1]
        curr_row = df.iloc[i]
        curr_no, prev_no = curr_row['No'], prev_row['No']
        
        limit_prev = prev_row['適用上限(m3)']
        unit_prev = prev_row['単位料金']
        unit_curr = curr_row['単位料金']
        
        base_prev = bases.get(prev_no, 0)
        base_curr = base_prev + (unit_prev - unit_curr) * limit_prev
        bases[curr_no] = base_curr
    return bases

def solve_unit(df_input, base_a, unit_a):
    df = df_input.copy().sort_values('No').reset_index(drop=True)
    if df.empty: return {}

    first_no = df.iloc[0]['No']
    units = {first_no: unit_a}
    
    input_bases = {first_no: base_a}
    for idx, row in df.iterrows():
        if idx > 0: input_bases[row['No']] = row['基本料金(入力)']

    for i in range(1, len(df)):
        prev_row = df.iloc[i-1]
        curr_row = df.iloc[i]
        curr_no, prev_no = curr_row['No'], prev_row['No']
        
        limit_prev = prev_row['適用上限(m3)']
        base_prev = input_bases.get(prev_no, 0)
        base_curr = input_bases.get(curr_no, 0)
        unit_prev = units.get(prev_no, 0)
        
        if limit_prev > 0:
            unit_curr = unit_prev - (base_curr - base_prev) / limit_prev
        else:
            unit_curr = 0
        units[curr_no] = unit_curr
    return units

# ---------------------------------------------------------
# 3. UI
# ---------------------------------------------------------
if 'calc_data' not in st.session_state:
    st.session_state.calc_data = pd.DataFrame({
        'No': [1, 2, 3],
        '区画名': ['A', 'B', 'C'],
        '適用上限(m3)': [8.0, 30.0, 99999.0],
        '基本料金(入力)': [1500.0, 2300.0, 5300.0],
        '単位料金(入力)': [500.0, 400.0, 300.0]
    })

tab1, tab2 = st.tabs(["🔄 従量料金基準", "🧮 基本料金基準"])

# === Tab 1: 従量料金基準 ===
with tab1:
    st.info("💡 **操作ガイド**: 左側の表にある「✏️」マークがついた列が入力可能です。")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        base_a_fwd = st.number_input("✏️ A区画 基本料金", value=1500.0, step=10.0, key="fwd_base_a")
        
        edited_fwd = st.data_editor(
            st.session_state.calc_data[['No', '区画名', '適用上限(m3)', '単位料金(入力)']],
            column_config={
                "No": st.column_config.NumberColumn(
                    label="🔒 No", 
                    disabled=True, 
                    width=60
                ),
                "区画名": st.column_config.TextColumn(
                    label="🔒 区画", 
                    disabled=True, 
                    width=80
                ),
                "適用上限(m3)": st.column_config.NumberColumn(
                    label="✏️ 適用上限 (変更可)", 
                    help="区画の境界値を変更します", 
                    format="%.1f",
                    required=True
                ),
                "単位料金(入力)": st.column_config.NumberColumn(
                    label="✏️ 単位料金 (入力)", 
                    help="ここを変数として入力します", 
                    format="%.2f",
                    required=True
                )
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_fwd"
        )
        
    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        if not edited_fwd.empty:
            calc_df = edited_fwd.rename(columns={'単位料金(入力)': '単位料金'})
            calc_df['単位料金'] = pd.to_numeric(calc_df['単位料金'], errors='coerce').fillna(0)
            calc_df['適用上限(m3)'] = pd.to_numeric(calc_df['適用上限(m3)'], errors='coerce').fillna(0)
            
            res_bases = solve_base(calc_df, base_a_fwd)
            
            res_list = []
            for idx, row in calc_df.sort_values('No').iterrows():
                no = row['No']
                res_list.append({
                    "No": no,
                    "区画": row['区画名'],
                    "適用上限": row['適用上限(m3)'],
                    "基本料金 (算出)": res_bases.get(no, 0),
                    "単位料金": row['単位料金']
                })
            
            # 色付け廃止、シンプル表示
            st.dataframe(
                pd.DataFrame(res_list).set_index('No').style.format({
                    "適用上限": "{:,.1f}",
                    "基本料金 (算出)": "{:,.2f}", 
                    "単位料金": "{:,.2f}"
                }),
                use_container_width=True,
                height=400
            )

# === Tab 2: 基本料金基準 ===
with tab2:
    st.info("💡 **操作ガイド**: 左側の表にある「✏️」マークがついた列が入力可能です。")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        cs1, cs2 = st.columns(2)
        base_a_rev = cs1.number_input("✏️ A区画 基本料金", value=1500.0, step=10.0, key="rev_base_a")
        unit_a_rev = cs2.number_input("✏️ A区画 単位料金", value=500.0, step=1.0, key="rev_unit_a")

        edited_rev = st.data_editor(
            st.session_state.calc_data[['No', '区画名', '適用上限(m3)', '基本料金(入力)']],
            column_config={
                "No": st.column_config.NumberColumn(
                    label="🔒 No", 
                    disabled=True, 
                    width=60
                ),
                "区画名": st.column_config.TextColumn(
                    label="🔒 区画", 
                    disabled=True, 
                    width=80
                ),
                "適用上限(m3)": st.column_config.NumberColumn(
                    label="✏️ 適用上限 (変更可)", 
                    format="%.1f",
                    required=True
                ),
                "基本料金(入力)": st.column_config.NumberColumn(
                    label="✏️ 基本料金 (目標)", 
                    help="設定したい基本料金を入力してください", 
                    format="%.2f",
                    required=True
                )
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_rev"
        )

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        if not edited_rev.empty:
            calc_df_rev = edited_rev.copy()
            calc_df_rev['基本料金(入力)'] = pd.to_numeric(calc_df_rev['基本料金(入力)'], errors='coerce').fillna(0)
            calc_df_rev['適用上限(m3)'] = pd.to_numeric(calc_df_rev['適用上限(m3)'], errors='coerce').fillna(0)

            res_units = solve_unit(calc_df_rev, base_a_rev, unit_a_rev)
            
            res_list = []
            for idx, row in calc_df_rev.sort_values('No').iterrows():
                no = row['No']
                base_val = base_a_rev if no == 1 else row['基本料金(入力)']
                
                res_list.append({
                    "No": no,
                    "区画": row['区画名'],
                    "適用上限": row['適用上限(m3)'],
                    "基本料金": base_val,
                    "単位料金 (算出)": res_units.get(no, 0)
                })
            
            # 色付け廃止、シンプル表示
            st.dataframe(
                pd.DataFrame(res_list).set_index('No').style.format({
                    "適用上限": "{:,.1f}",
                    "基本料金": "{:,.2f}", 
                    "単位料金 (算出)": "{:,.4f}"
                }), 
                use_container_width=True,
                height=400
            )
            
            st.info("💡 計算された「単位料金」がマイナスの場合は、基本料金の傾斜がきつすぎます。")

import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Calculator Style)
# ---------------------------------------------------------
# 【修正】layout="wide" に変更して横幅を最大化
st.set_page_config(page_title="Gasio 電卓", page_icon="🧮", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; margin-bottom: 20px;}
    .stNumberInput input { font-weight: bold; color: #2c3e50; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 電卓</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Rate Design Solver</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 計算ロジック (堅牢化版)
# ---------------------------------------------------------

def solve_base(df_input, base_a):
    """ 順算: 従量料金(Unit)から基本料金(Base)を算出 """
    df = df_input.copy().sort_values('No').reset_index(drop=True)
    if df.empty: return {}

    first_no = df.iloc[0]['No']
    bases = {first_no: base_a}
    
    for i in range(1, len(df)):
        prev_row = df.iloc[i-1]
        curr_row = df.iloc[i]
        
        curr_no = curr_row['No']
        prev_no = prev_row['No']
        
        limit_prev = prev_row['適用上限(m3)']
        unit_prev = prev_row['単位料金']
        unit_curr = curr_row['単位料金']
        
        base_prev = bases.get(prev_no, 0)
        base_curr = base_prev + (unit_prev - unit_curr) * limit_prev
        bases[curr_no] = base_curr
        
    return bases

def solve_unit(df_input, base_a, unit_a):
    """ 逆算: 基本料金(Base)から従量料金(Unit)を算出 """
    df = df_input.copy().sort_values('No').reset_index(drop=True)
    if df.empty: return {}

    first_no = df.iloc[0]['No']
    units = {first_no: unit_a}
    
    input_bases = {}
    input_bases[first_no] = base_a
    for idx, row in df.iterrows():
        if idx > 0:
            input_bases[row['No']] = row['基本料金(入力)']

    for i in range(1, len(df)):
        prev_row = df.iloc[i-1]
        curr_row = df.iloc[i]
        
        curr_no = curr_row['No']
        prev_no = prev_row['No']
        
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

# 初期データ
if 'calc_data' not in st.session_state:
    st.session_state.calc_data = pd.DataFrame({
        'No': [1, 2, 3],
        '区画名': ['A', 'B', 'C'],
        '適用上限(m3)': [20.0, 100.0, 99999.0],
        '基本料金(入力)': [1000.0, 1500.0, 2500.0], # 逆算用
        '単位料金(入力)': [150.0, 140.0, 130.0]     # 順算用
    })

tab1, tab2 = st.tabs(["🔄 順算 (従量 → 基本)", "🧮 逆算 (基本 → 従量)"])

# === Tab 1: 順算モード ===
with tab1:
    st.caption("従量単価を決めて、基本料金を自動計算します")
    
    # 【修正】カラム比率を変更し、テーブルエリアを拡張
    c1, c2 = st.columns([4, 6])
    
    with c1:
        st.markdown("##### 1. パラメータ入力")
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
        st.markdown("##### 2. 計算結果")
        if not edited_fwd.empty:
            calc_df = edited_fwd.rename(columns={'単位料金(入力)': '単位料金'})
            
            # 型変換の安全策
            calc_df['単位料金'] = pd.to_numeric(calc_df['単位料金'], errors='coerce').fillna(0)
            calc_df['適用上限(m3)'] = pd.to_numeric(calc_df['適用上限(m3)'], errors='coerce').fillna(0)
            
            res_bases = solve_base(calc_df, base_a_fwd)
            
            res_list = []
            for idx, row in calc_df.sort_values('No').iterrows():
                no = row['No']
                res_list.append({
                    "No": no, # Noも表示
                    "区画": row['区画名'],
                    "適用上限": row['適用上限(m3)'],
                    "基本料金 (算出)": res_bases.get(no, 0),
                    "単位料金": row['単位料金']
                })
            
            # 結果テーブルを大きく表示
            st.dataframe(
                pd.DataFrame(res_list).set_index('No').style.format({
                    "適用上限": "{:,.1f}",
                    "基本料金 (算出)": "{:,.2f}", 
                    "単位料金": "{:,.2f}"
                }),
                use_container_width=True,
                height=400 # 高さを指定して見やすく
            )


# === Tab 2: 逆算モード ===
with tab2:
    st.caption("基本料金を先に決めて、整合する従量単価を逆算します")
    
    c1, c2 = st.columns([4, 6])
    
    with c1:
        st.markdown("##### 1. パラメータ入力")
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
        st.markdown("##### 2. 計算結果")
        if not edited_rev.empty:
            calc_df_rev = edited_rev.copy()
            calc_df_rev['基本料金(入力)'] = pd.to_numeric(calc_df_rev['基本料金(入力)'], errors='coerce').fillna(0)
            calc_df_rev['適用上限(m3)'] = pd.to_numeric(calc_df_rev['適用上限(m3)'], errors='coerce').fillna(0)

            res_units = solve_unit(calc_df_rev, base_a_rev, unit_a_rev)
            
            res_list = []
            for idx, row in calc_df_rev.sort_values('No').iterrows():
                no = row['No']
                if no == 1:
                    base_val = base_a_rev 
                else:
                    base_val = row['基本料金(入力)']
                
                res_list.append({
                    "No": no,
                    "区画": row['区画名'],
                    "適用上限": row['適用上限(m3)'],
                    "基本料金": base_val,
                    "単位料金 (算出)": res_units.get(no, 0)
                })
            
            st.dataframe(
                pd.DataFrame(res_list).set_index('No').style.format({
                    "適用上限": "{:,.1f}",
                    "基本料金": "{:,.2f}", 
                    "単位料金 (算出)": "{:,.4f}"
                }), 
                use_container_width=True,
                height=400
            )
            
            st.info("💡 「単位料金」がマイナスになる場合は、基本料金の傾斜がきつすぎます。")
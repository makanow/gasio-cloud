import streamlit as st
import pandas as pd
import numpy as np

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
st.markdown('<div class="sub-title">Rate Design Solver (Robust Auto-Indexing)</div>', unsafe_allow_html=True)

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
    """Noneの行を含めて強制的に再採番し、最終行を固定する"""
    if df.empty: return df
    
    # 物理的なインデックスに合わせてNoと区画名を強制上書き
    df = df.reset_index(drop=True)
    df['No'] = range(1, len(df) + 1)
    df['区画名'] = [get_alpha_label(i) for i in range(len(df))]
    
    # 数値が入っていない列(None/NaN)を数値型に変換し、デフォルト値を0.0に設定
    df['適用上限(m3)'] = pd.to_numeric(df['適用上限(m3)'], errors='coerce').fillna(0.0)
    df['単位料金(入力)'] = pd.to_numeric(df['単位料金(入力)'], errors='coerce').fillna(0.0)
    
    # 最終行の適用上限を 99999.0 に固定
    df.loc[df.index[-1], '適用上限(m3)'] = 99999.0
    return df

def solve_base(df_input, base_a):
    """基本料金の算出ロジック (従量料金基準)"""
    df = df_input.copy().sort_values('No').reset_index(drop=True)
    if df.empty: return {}
    
    first_no = df.iloc[0]['No']
    bases = {first_no: base_a}
    
    for i in range(1, len(df)):
        prev_row = df.iloc[i-1]
        curr_row = df.iloc[i]
        
        limit_prev = prev_row['適用上限(m3)']
        unit_prev = prev_row['単位料金']
        unit_curr = curr_row['単位料金']
        
        base_prev = bases.get(prev_row['No'], 0)
        # 次の区画の基本料金 = 前の基本料金 + (前の単価 - 今の単価) * 前の適用上限
        base_curr = base_prev + (unit_prev - unit_curr) * limit_prev
        bases[curr_row['No']] = base_curr
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
    st.session_state.calc_data = initial_df

tab1, tab2 = st.tabs(["🔄 従量料金基準", "🧮 基本料金基準"])

# --- Tab 1: 従量料金基準 ---
with tab1:
    st.info("💡 操作ガイド: 行を追加・削除すると、Noと区画名は自動で再採番されます。最終行の上限は99999に固定されます。")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        # 第1区画の基本料金入力
        current_base_a = float(st.session_state.calc_data.iloc[0]['基本料金(入力)']) if not st.session_state.calc_data.empty else 1500.0
        base_a_fwd = st.number_input("✏️ 第1区画(A) 基本料金", value=current_base_a, step=10.0, key="input_base_a")
        
        # 編集対象の列
        cols_to_edit = ['No', '区画名', '適用上限(m3)', '単位料金(入力)']
        
        # data_editor の実行
        edited_fwd = st.data_editor(
            st.session_state.calc_data[cols_to_edit],
            column_config={
                "No": st.column_config.NumberColumn("🔒 No", disabled=True, width=50),
                "区画名": st.column_config.TextColumn("🔒 区画", disabled=True, width=70),
                "適用上限(m3)": st.column_config.NumberColumn("✏️ 適用上限", format="%.1f", required=True),
                "単位料金(入力)": st.column_config.NumberColumn("✏️ 単位料金", format="%.2f", required=True)
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_fwd"
        )
        
        # データの変更または行の追加・削除があった場合の同期処理
        if not edited_fwd.equals(st.session_state.calc_data[cols_to_edit]):
            # 安定化処理 (再採番・最終行固定・None補完)
            new_df = stabilize_dataframe(edited_fwd)
            
            # 基本料金(入力)などの隠し列を維持しつつ更新
            new_master = new_df.copy()
            if '基本料金(入力)' in st.session_state.calc_data.columns:
                # Noをキーに結合して既存の基本料金を維持
                new_master = new_master.merge(
                    st.session_state.calc_data[['No', '基本料金(入力)']], 
                    on='No', 
                    how='left'
                ).fillna({'基本料金(入力)': 0.0})
            
            st.session_state.calc_data = new_master
            st.rerun()

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        if not st.session_state.calc_data.empty:
            # 計算用にカラム名を合わせる
            calc_df = st.session_state.calc_data.copy().rename(columns={'単位料金(入力)': '単位料金'})
            res_bases = solve_base(calc_df, base_a_fwd)
            
            # 安全なリスト構築
            res_list = []
            for _, r in calc_df.iterrows():
                # 数値が有効な行のみ計算結果に含める
                if pd.notnull(r['No']):
                    res_list.append({
                        "No": int(r['No']), 
                        "区画名": r['区画名'], 
                        "適用上限": r['適用上限(m3)'], 
                        "基本料金(算出)": res_bases.get(r['No'], 0), 
                        "単位料金": r['単位料金']
                    })
            
            if res_list:
                st.dataframe(
                    pd.DataFrame(res_list).set_index('No').style.format({
                        "適用上限": "{:,.1f}", 
                        "基本料金(算出)": "{:,.2f}", 
                        "単位料金": "{:,.2f}"
                    }), 
                    use_container_width=True, 
                    height=400
                )

# --- Tab 2: 基本料金基準 (今回はTab 1の修正に注力) ---
with tab2:
    st.write("※現在は『従量料金基準』のアップデートを優先しています。")

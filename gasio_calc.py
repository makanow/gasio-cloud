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
st.markdown('<div class="sub-title">Rate Design Solver (Bug Fixed)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ロジック (アルファベット生成 & 安定化)
# ---------------------------------------------------------

def get_alpha_label(n):
    label = ""
    while n >= 0:
        label = chr(n % 26 + 65) + label
        n = n // 26 - 1
    return label

def stabilize_dataframe(df):
    """入力値を元に、Noと区画名を物理的に強制上書きする"""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=['No', '区画名', '適用上限(m3)', '単位料金(入力)'])
    
    # 行追加・削除に対応してインデックスとNo、区画名を即座に振り直す
    df = df.reset_index(drop=True)
    df['No'] = range(1, len(df) + 1)
    df['区画名'] = [get_alpha_label(i) for i in range(len(df))]
    
    # 数値変換の強制 (None/NaN対策)
    df['適用上限(m3)'] = pd.to_numeric(df['適用上限(m3)'], errors='coerce').fillna(0.0)
    df['単位料金(入力)'] = pd.to_numeric(df['単位料金(入力)'], errors='coerce').fillna(0.0)
    
    # 最終行の固定
    df.loc[df.index[-1], '適用上限(m3)'] = 99999.0
    return df

def solve_base(df, base_a):
    """従量料金から各区画の基本料金を算出する"""
    if df.empty: return {}
    bases = {1: base_a}
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        # 計算式: 前の基本料金 + (前の単価 - 今の単価) * 前の適用上限
        bases[curr['No']] = bases[prev['No']] + (prev['単位料金(入力)'] - curr['単位料金(入力)']) * prev['適用上限(m3)']
    return bases

# ---------------------------------------------------------
# 3. メイン UI
# ---------------------------------------------------------

if 'calc_data' not in st.session_state:
    # 初期の3区画設定
    st.session_state.calc_data = pd.DataFrame([
        {'No': 1, '区画名': 'A', '適用上限(m3)': 8.0, '単位料金(入力)': 500.0},
        {'No': 2, '区画名': 'B', '適用上限(m3)': 30.0, '単位料金(入力)': 400.0},
        {'No': 3, '区画名': 'C', '適用上限(m3)': 99999.0, '単位料金(入力)': 300.0}
    ])

tab1, tab2 = st.tabs(["🔄 従量料金基準", "🧮 基本料金基準"])

with tab1:
    st.info("💡 行を追加すると、即座にNoと区画名が更新されます。最終行の上限は99999に固定されます。")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        base_a_fwd = st.number_input("✏️ 第1区画(A) 基本料金", value=1500.0, step=10.0)
        
        # 入力エディタ
        edited_df = st.data_editor(
            st.session_state.calc_data,
            column_config={
                "No": st.column_config.NumberColumn("🔒 No", disabled=True, width=50),
                "区画名": st.column_config.TextColumn("🔒 区画", disabled=True, width=70),
                "適用上限(m3)": st.column_config.NumberColumn("✏️ 適用上限", format="%.1f"),
                "単位料金(入力)": st.column_config.NumberColumn("✏️ 単位料金", format="%.2f")
            },
            num_rows="dynamic",
            use_container_width=True,
            key="gas_editor"
        )
        
        # 変更があれば再採番と再計算を実行
        if len(edited_df) != len(st.session_state.calc_data) or not edited_df.equals(st.session_state.calc_data):
            st.session_state.calc_data = stabilize_dataframe(edited_df)
            st.rerun()

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        res_df = st.session_state.calc_data.copy()
        if not res_df.empty:
            res_bases = solve_base(res_df, base_a_fwd)
            res_df['基本料金(算出)'] = res_df['No'].map(res_bases)
            
            # 列の表示順を整える
            display_df = res_df[['No', '区画名', '適用上限(m3)', '基本料金(算出)', '単位料金(入力)']].copy()
            display_df.columns = ['No', '区画名', '適用上限', '基本料金(算出)', '単位料金']
            
            # エラー対策: 数値列のみを指定してフォーマットを適用
            st.dataframe(
                display_df.set_index('No').style.format({
                    '適用上限': "{:,.1f}",
                    '基本料金(算出)': "{:,.2f}",
                    '単位料金': "{:,.2f}"
                }), 
                use_container_width=True, height=400
            )

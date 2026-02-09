# --- (中略: デザイン・計算ロジック部分は変更なし) ---

# ---------------------------------------------------------
# 3. UI & ステート管理 (No.・区画名の完全自動採番版)
# ---------------------------------------------------------

def stabilize_dataframe(df):
    if df.empty:
        return df
    
    # 1. No. を上から順に振り直す (1, 2, 3...)
    df = df.reset_index(drop=True)
    df['No'] = df.index + 1
    
    # 2. 区画名をアルファベット順に自動生成 (A, B, C... Z, AA, AB...)
    def get_alpha_label(n):
        label = ""
        while n >= 0:
            label = chr(n % 26 + 65) + label
            n = n // 26 - 1
        return label
    
    df['区画名'] = [get_alpha_label(i) for i in range(len(df))]
    
    # 3. 最終行の適用上限を 99999.0 に固定
    df.loc[df.index[-1], '適用上限(m3)'] = 99999.0
    return df

if 'calc_data' not in st.session_state:
    # 初期データも関数を通して生成
    initial_df = pd.DataFrame({
        'No': [1, 2, 3],
        '区画名': ['', '', ''],
        '適用上限(m3)': [8.0, 30.0, 0.0],
        '基本料金(入力)': [1500.0, 2300.0, 5300.0],
        '単位料金(入力)': [500.0, 400.0, 300.0]
    })
    st.session_state.calc_data = stabilize_dataframe(initial_df)

tab1, tab2 = st.tabs(["🔄 従量料金基準", "🧮 基本料金基準"])

# --- Tab 1: 従量料金基準 ---
with tab1:
    st.info("💡 **Gas Lab Style**: 行を追加・削除すると、「No」と「区画名」は自動的に再計算されます。")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        base_a_fwd = st.number_input("✏️ 第1区画(A) 基本料金", value=float(st.session_state.calc_data.iloc[0]['基本料金(入力)']), step=10.0, key="fwd_base_a")
        
        # 編集対象の列を定義 (Noと区画名は閲覧のみ)
        cols_to_edit = ['No', '区画名', '適用上限(m3)', '単位料金(入力)']
        edited_fwd = st.data_editor(
            st.session_state.calc_data[cols_to_edit],
            column_config={
                "No": st.column_config.NumberColumn(label="🔒 No", disabled=True, width=50),
                "区画名": st.column_config.TextColumn(label="🔒 区画", disabled=True, width=70),
                "適用上限(m3)": st.column_config.NumberColumn(label="✏️ 適用上限", format="%.1f", required=True),
                "単位料金(入力)": st.column_config.NumberColumn(label="✏️ 単位料金", format="%.2f", required=True)
            },
            num_rows="dynamic", use_container_width=True, key="editor_fwd"
        )
        
        if not edited_fwd.equals(st.session_state.calc_data[cols_to_edit]):
            new_df = stabilize_dataframe(edited_fwd)
            new_master = new_df.copy()
            current_master = st.session_state.calc_data[['No', '基本料金(入力)']]
            new_master = new_master.merge(current_master, on='No', how='left').fillna(0.0)
            
            st.session_state.calc_data = new_master
            st.rerun()

    # --- (以下、Result表示は前回のコードと同様のため省略) ---

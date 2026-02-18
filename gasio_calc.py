import streamlit as st
import pandas as pd
import numpy as np
import io

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio 電卓", page_icon="🧮", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; text-align: left; margin-bottom: 0; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; text-align: left; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .hayami-header { background-color: #2c3e50; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> <span style="color:#2c3e50">電卓</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Rate Design Solver (Integrated Stable Build)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. ロジック (アルファベット生成 & 算出)
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
    bases = {sorted_df.iloc[0]['No']: base_a}
    for i in range(1, len(sorted_df)):
        prev, curr = sorted_df.iloc[i-1], sorted_df.iloc[i]
        bases[curr['No']] = bases[prev['No']] + (prev['単位料金(入力)'] - curr['単位料金(入力)']) * prev['適用上限(m3)']
    return bases

def solve_unit(df, unit_a):
    if df.empty: return {}
    sorted_df = df.sort_values('No')
    units = {sorted_df.iloc[0]['No']: unit_a}
    for i in range(1, len(sorted_df)):
        prev, curr = sorted_df.iloc[i-1], sorted_df.iloc[i]
        if prev['適用上限(m3)'] != 0:
            units[curr['No']] = units[prev['No']] - (curr['基本料金(入力)'] - prev['基本料金(入力)']) * prev['適用上限(m3)']
        else:
            units[curr['No']] = units[prev['No']]
    return units

def stabilize_dataframe(df, start_val, mode='fwd'):
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=['No', '区画名', '適用上限(m3)', '単位料金(入力)', '基本料金(入力)', '基本料金(算出)', '単位料金(算出)'])
    
    df = df.reset_index(drop=True)
    df['No'] = range(1, len(df) + 1)
    df['区画名'] = [get_alpha_label(i) for i in range(len(df))]
    
    for col in ['適用上限(m3)', '単位料金(入力)', '基本料金(入力)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        else:
            df[col] = 0.0

    df.loc[df.index[-1], '適用上限(m3)'] = 99999.0

    if mode == 'fwd':
        res = solve_base(df, start_val)
        df['基本料金(算出)'] = df['No'].map(res)
    else:
        res = solve_unit(df, start_val)
        df['単位料金(算出)'] = df['No'].map(res)
        
    return df

# ---------------------------------------------------------
# 3. 早見表ジェネレーター ロジック
# ---------------------------------------------------------
def calc_bill(usage, df_rates):
    target = df_rates[df_rates['適用上限(m3)'] >= (usage - 1e-9)]
    row = target.iloc[0] if not target.empty else df_rates.iloc[-1]
    # ガス料金は通常、小数点以下切り捨て
    return int(row['基本料金'] + (usage * row['調整単位料金']))

def generate_hayami_tables(df_rates, adj_rate):
    df = df_rates.copy()
    df['調整単位料金'] = df['単位料金'] + adj_rate

    # 表1: 0.0 ~ 40.9 (0.1刻み)
    t1 = []
    for i in range(41):
        r = {"m³": i}
        for j in range(10):
            r[f"0.{j}"] = calc_bill(i + j*0.1, df)
        t1.append(r)
    
    # 表2: 40 ~ 209 (1.0刻み、10行ごと)
    t2 = []
    for i in range(40, 201, 10):
        r = {"m³": i}
        for j in range(10):
            if i == 40 and j == 0:
                r[str(j)] = np.nan # 40.0は表1にあるため空欄
            else:
                r[str(j)] = calc_bill(i + j, df)
        t2.append(r)

    return pd.DataFrame(t1), pd.DataFrame(t2), df

def render_hayami_generator(df_base, base_col, unit_col, tab_key):
    st.markdown("---")
    
    # st.expander で全体を包み、デフォルトを折りたたみに設定
    with st.expander("📄 ガス料金早見表 ジェネレーター（クリックで展開）", expanded=False):
        st.markdown("算出された基本料金・単位料金に**「原料費調整単価」**を加減算し、実運用向けの早見表を自動生成します。")
        
        col_in, col_dummy = st.columns([1, 2])
        with col_in:
            adj_rate = st.number_input("⚡ 原料費調整単価 (円/m³)", value=0.00, step=0.10, format="%.2f", key=f"adj_{tab_key}")

        # データ整形
        calc_df = df_base[['区画名', '適用上限(m3)', base_col, unit_col]].copy()
        calc_df.columns = ['区画名', '適用上限(m3)', '基本料金', '単位料金']
        
        # 表生成
        df_t1, df_t2, df_adj = generate_hayami_tables(calc_df, adj_rate)

        st.markdown("**【適用される料金表（調整後）】**")
        st.dataframe(df_adj.style.format({
            "適用上限(m3)": "{:,.1f}", "基本料金": "¥{:,.2f}", "単位料金": "¥{:,.2f}", "調整単位料金": "¥{:,.2f}"
        }), use_container_width=True, hide_index=True)

        # 早見表の表示設定
        fmt1 = {col: "{:,.0f}" for col in df_t1.columns if col != "m³"}
        fmt2 = {col: "{:,.0f}" for col in df_t2.columns if col != "m³"}

        st.markdown('<div class="hayami-header">▼ 早見表 ①（0.0m³ 〜 40.9m³）※0.1m³刻み</div>', unsafe_allow_html=True)
        st.dataframe(df_t1.style.format(fmt1).hide(axis="index"), use_container_width=True)

        st.markdown('<div class="hayami-header">▼ 早見表 ②（40m³ 〜 209m³）※1.0m³刻み</div>', unsafe_allow_html=True)
        st.dataframe(df_t2.style.format(fmt2, na_rep="-").hide(axis="index"), use_container_width=True)

        # --- Excelダウンロード機能 ---
        output = io.BytesIO()
        # engine='xlsxwriter' または 'openpyxl' が必要です（多くのStreamlit環境にはどちらか入っています）
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_adj.to_excel(writer, index=False, sheet_name='1. 適用料金表')
                df_t1.to_excel(writer, index=False, sheet_name='2. 早見表(0.0-40.9)')
                df_t2.to_excel(writer, index=False, sheet_name='3. 早見表(40-209)')
        except ValueError:
            # xlsxwriterが無い場合は openpyxl でフォールバック
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_adj.to_excel(writer, index=False, sheet_name='1. 適用料金表')
                df_t1.to_excel(writer, index=False, sheet_name='2. 早見表(0.0-40.9)')
                df_t2.to_excel(writer, index=False, sheet_name='3. 早見表(40-209)')

        excel_data = output.getvalue()
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 この早見表をExcelでダウンロード（印刷・PDF化用）",
            data=excel_data,
            file_name=f"ガス料金早見表_調整単価{adj_rate}円.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            key=f"dl_excel_{tab_key}" # タブごとのキー被りを防止
        )

# ---------------------------------------------------------
# 4. メイン UI
# ---------------------------------------------------------
if 'calc_data' not in st.session_state:
    st.session_state.calc_data = pd.DataFrame([
        {'No': 1, '区画名': 'A', '適用上限(m3)': 8.0, '単位料金(入力)': 650.0, '基本料金(入力)': 1500.0},
        {'No': 2, '区画名': 'B', '適用上限(m3)': 30.0, '単位料金(入力)': 550.0, '基本料金(入力)': 2300.0},
        {'No': 3, '区画名': 'C', '適用上限(m3)': 99999.0, '単位料金(入力)': 450.0, '基本料金(入力)': 5300.0}
    ])
    st.session_state.last_base_a = 1500.0
    st.session_state.last_unit_a = 650.0

tab1, tab2 = st.tabs(["🔄 従量料金基準", "🧮 基本料金基準"])

# --- Tab 1: 従量料金基準 ---
with tab1:
    st.info("💡 操作ガイド: 単位料金を入力すると基本料金が自動計算されます。")
    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        base_a_fwd = st.number_input("✏️ 第1区画(A) 基本料金", value=float(st.session_state.last_base_a), step=10.0, key="fwd_start")
        current_df = stabilize_dataframe(st.session_state.calc_data, base_a_fwd, mode='fwd')
        
        edited_fwd = st.data_editor(
            current_df[['No', '区画名', '適用上限(m3)', '単位料金(入力)', '基本料金(算出)']],
            column_config={
                "No": st.column_config.NumberColumn("🔒 No", disabled=True, width=40),
                "区画名": st.column_config.TextColumn("🔒 区画", disabled=True, width=60),
                "適用上限(m3)": st.column_config.NumberColumn("✏️ 適用上限", format="%.1f"),
                "単位料金(入力)": st.column_config.NumberColumn("✏️ 単位料金", format="%.2f"),
                "基本料金(算出)": st.column_config.NumberColumn("📊 基本料金(自算)", disabled=True, format="%.2f")
            },
            num_rows="dynamic", use_container_width=True, key="editor_fwd"
        )
        
        if base_a_fwd != st.session_state.last_base_a or not edited_fwd.equals(current_df[['No', '区画名', '適用上限(m3)', '単位料金(入力)', '基本料金(算出)']]):
            st.session_state.last_base_a = base_a_fwd
            st.session_state.calc_data.update(edited_fwd)
            if len(edited_fwd) != len(st.session_state.calc_data):
                 st.session_state.calc_data = stabilize_dataframe(edited_fwd, base_a_fwd, mode='fwd')
            st.rerun()

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        if not edited_fwd.empty:
            st.dataframe(
                edited_fwd.set_index('No')[['区画名', '適用上限(m3)', '単位料金(入力)', '基本料金(算出)']].style.format({
                    '適用上限(m3)': "{:,.1f}",
                    '単位料金(入力)': "{:,.2f}",
                    '基本料金(算出)': "{:,.2f}"
                }), 
                use_container_width=True
            )

    # 早見表ジェネレーター呼び出し
    if not edited_fwd.empty:
        render_hayami_generator(edited_fwd, base_col='基本料金(算出)', unit_col='単位料金(入力)', tab_key='fwd')

# --- Tab 2: 基本料金基準 ---
with tab2:
    st.info("💡 操作ガイド: 基本料金を入力すると単位料金が自動計算されます。")
    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.markdown("##### 1. パラメータ入力 (Input)")
        unit_a_rev = st.number_input("✏️ 第1区画(A) 単位料金", value=float(st.session_state.last_unit_a), step=1.0, key="rev_start")
        current_df_rev = stabilize_dataframe(st.session_state.calc_data, unit_a_rev, mode='rev')
        
        edited_rev = st.data_editor(
            current_df_rev[['No', '区画名', '適用上限(m3)', '基本料金(入力)', '単位料金(算出)']],
            column_config={
                "No": st.column_config.NumberColumn("🔒 No", disabled=True, width=40),
                "区画名": st.column_config.TextColumn("🔒 区画", disabled=True, width=60),
                "適用上限(m3)": st.column_config.NumberColumn("✏️ 適用上限", format="%.1f"),
                "基本料金(入力)": st.column_config.NumberColumn("✏️ 基本料金", format="%.2f"),
                "単位料金(算出)": st.column_config.NumberColumn("📊 単位料金(自算)", disabled=True, format="%.2f")
            },
            num_rows="dynamic", use_container_width=True, key="editor_rev"
        )
        
        if unit_a_rev != st.session_state.last_unit_a or not edited_rev.equals(current_df_rev[['No', '区画名', '適用上限(m3)', '基本料金(入力)', '単位料金(算出)']]):
            st.session_state.last_unit_a = unit_a_rev
            st.session_state.calc_data.update(edited_rev)
            if len(edited_rev) != len(st.session_state.calc_data):
                st.session_state.calc_data = stabilize_dataframe(edited_rev, unit_a_rev, mode='rev')
            st.rerun()

    with c2:
        st.markdown("##### 2. 計算結果 (Result)")
        if not edited_rev.empty:
            res_rev = edited_rev.set_index('No')[['区画名', '適用上限(m3)', '単位料金(算出)', '基本料金(入力)']]
            st.dataframe(res_rev.style.format({
                    '適用上限(m3)': "{:,.1f}",
                    '単位料金(算出)': "{:,.2f}",
                    '基本料金(入力)': "{:,.2f}"
                }), use_container_width=True)

    # 早見表ジェネレーター呼び出し
    if not edited_rev.empty:
        render_hayami_generator(edited_rev, base_col='基本料金(入力)', unit_col='単位料金(算出)', tab_key='rev')

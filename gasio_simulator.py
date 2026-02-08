import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Style)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    .stMetric { background-color: #fdfdfd; padding: 10px 15px; border-radius: 6px; border-left: 5px solid #3498db; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown('<div class="main-title">Gasio 計算機</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cloud Edition - Rate Simulation System</div>', unsafe_allow_html=True)

if 'simulation_result' not in st.session_state: st.session_state.simulation_result = None
if 'plan_data' not in st.session_state:
    d_df = pd.DataFrame({'No': [1, 2, 3], '区画名': ['A', 'B', 'C'], '適用上限(m3)': [8.0, 30.0, 99999.0], '単位料金': [500.0, 400.0, 300.0]})
    st.session_state.plan_data = {i: d_df.copy() for i in range(3)}
    st.session_state.base_a = {i: 1500.0 for i in range(3)}

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def smart_read_csv(file):
    """文字コードを自動判別して読み込むロジック"""
    encodings = ['utf-8-sig', 'cp932', 'utf-8', 'shift_jis']
    for enc in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return None

def normalize_columns(df):
    if df is None: return None
    rename_map = {'基本':'基本料金','基礎料金':'基本料金','ID':'料金表番号','Usage':'使用量','調定':'調定数','適用上限':'MAX', '適用上限(m3)':'MAX'}
    df = df.rename(columns=rename_map)
    for c in ['使用量', 'MAX', '調定数']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0 if c!='MAX' else 999999999.0)
    return df

def get_template_csv(csv_type="usage"):
    if csv_type == "usage":
        return pd.DataFrame({'料金表番号': [10, 11], '使用量': [15.5, 24.0], '調定数': [1, 1]}).to_csv(index=False).encode('utf-8-sig')
    return pd.DataFrame({'料金表番号': [10, 10, 10], '区画': ['A', 'B', 'C'], 'MIN': [0.0, 8.0, 30.0], 'MAX': [8.0, 30.0, 99999.0], '基本料金': [1500, 2300, 5300], '単位料金': [500.0, 400.0, 300.0]}).to_csv(index=False).encode('utf-8-sig')

def calculate_slide_rates(base_a, blocks_df):
    blocks = blocks_df.copy().sort_values('No')
    base_fees = {blocks.iloc[0]['No']: base_a}
    for i in range(1, len(blocks)):
        p, c = blocks.iloc[i-1], blocks.iloc[i]
        base_fees[c['No']] = base_fees[p['No']] + (p['単位料金'] - c['単位料金']) * p['適用上限(m3)']
    return base_fees

def calculate_bill_single(usage, tariff_df, billing_count=1):
    if billing_count == 0 or tariff_df.empty: return 0
    df = tariff_df.copy()
    if '適用上限(m3)' in df.columns: df = df.rename(columns={'適用上限(m3)':'MAX'})
    df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    target = df[df['MAX'] >= (usage - 1e-9)].sort_values('MAX')
    row = target.iloc[0] if not target.empty else df.sort_values('MAX').iloc[-1]
    return int(row.get('基本料金', 0) + (usage * row['単位料金']))

# ---------------------------------------------------------
# 3. サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    with st.expander("📥 テンプレートをダウンロード"):
        st.download_button("1. 使用量CSVテンプレート", get_template_csv("usage"), "template_usage.csv", "text/csv")
        st.download_button("2. 料金表マスタテンプレート", get_template_csv("master"), "template_master.csv", "text/csv")
    
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'])
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'])
    
    selected_ids = []
    if file_master:
        df_master_all = normalize_columns(smart_read_csv(file_master))
        if df_master_all is not None:
            u_ids = sorted(df_master_all['料金表番号'].unique())
            selected_ids = st.multiselect("対象料金表", u_ids, default=u_ids)

# ---------------------------------------------------------
# 4. メインエリア
# ---------------------------------------------------------
if file_usage and file_master and selected_ids:
    df_usage = normalize_columns(smart_read_csv(file_usage))
    if df_usage is not None:
        df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
        
        tab_design, tab_sim = st.tabs(["Design", "Simulation"])

        with tab_design:
            new_plans = {}
            for i in range(3):
                st.session_state.base_a[i] = st.number_input(f"Plan {i+1} A区画 基本料金", value=st.session_state.base_a[i], key=f"ba_{i}")
                edited = st.data_editor(st.session_state.plan_data[i], use_container_width=True, key=f"ed_{i}")
                st.session_state.plan_data[i] = edited
                bases = calculate_slide_rates(st.session_state.base_a[i], edited)
                new_plans[f"Plan_{i+1}"] = pd.DataFrame([{"区画名":r['区画名'], "適用上限(m3)":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']} for _, r in edited.iterrows()])

        with tab_sim:
            if st.button("🚀 計算実行", type="primary"):
                res = df_target_usage.copy()
                res['現行料金'] = res.apply(lambda r: calculate_bill_single(r['使用量'], df_master_all[df_master_all['料金表番号']==r['料金表番号']], r['調定数']), axis=1)
                for pn, pdf in new_plans.items():
                    res[pn] = res.apply(lambda r: calculate_bill_single(r['使用量'], pdf, r['調定数']), axis=1)
                st.session_state.simulation_result = res
            
            if st.session_state.simulation_result is not None:
                sr = st.session_state.simulation_result
                sel_p = st.selectbox("比較対象プラン", list(new_plans.keys()))
                sr['影響額'] = sr[sel_p] - sr['現行料金']
                
                col1, col2 = st.columns(2)
                col1.metric("総影響額", f"¥{sr['影響額'].sum():,.0f}")
                col2.metric("平均影響額", f"¥{sr['影響額'].mean():,.0f}")

                gc1, gc2 = st.columns(2)
                with gc1:
                    fig_hist = px.histogram(sr, x="影響額", title="顧客別 影響額分布", labels={'影響額': '負担増減額 (円)'})
                    fig_hist.add_vline(x=0, line_dash="dash", line_color="black")
                    st.plotly_chart(fig_hist, use_container_width=True)
                with gc2:
                    st.plotly_chart(px.scatter(sr.sample(min(len(sr),1000)), x='使用量', y='影響額', title="使用量別 影響インパクト"), use_container_width=True)
else:
    st.info("👈 サイドバーからCSVをアップロードしてください")

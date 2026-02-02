import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import json
import datetime
import base64

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Style)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; overflow-wrap: break-word; }
    [data-testid="stDataEditor"] div[data-testid="stTable"] td[aria-readonly="false"] { border-right: 5px solid #fdd835 !important; background-color: #fffde7 !important; }
    .stMetric { background-color: #fdfdfd; padding: 10px 15px; border-radius: 6px; border-left: 5px solid #3498db; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 計算機</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Cloud Edition - Executive Simulation System</div>', unsafe_allow_html=True)

# ステート管理
if 'simulation_result' not in st.session_state: st.session_state.simulation_result = None
if 'plan_data' not in st.session_state:
    d_df = pd.DataFrame({'No': [1, 2, 3], '区画名': ['A', 'B', 'C'], '適用上限(m3)': [8.0, 30.0, 99999.0], '単位料金': [500.0, 400.0, 300.0]})
    st.session_state.plan_data = {i: d_df.copy() for i in range(5)}
    st.session_state.base_a = {i: 1500.0 for i in range(5)}

CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
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

def smart_load_wrapper(file):
    for enc in ['cp932', 'utf-8', 'shift_jis']:
        try:
            file.seek(0); df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            # Normalize
            rename_map = {'基本':'基本料金','上限':'MAX','ID':'料金表番号','Usage':'使用量','調定':'調定数'}
            df = df.rename(columns=rename_map)
            for c in ['使用量', 'MAX', '調定数']:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            if '料金表番号' not in df.columns: df['料金表番号'] = 10
            return df
        except: continue
    return None

# ---------------------------------------------------------
# 3. PDF用HTMLレポート生成
# ---------------------------------------------------------
def get_pdf_report_html(summ_df):
    # HTMLレポートを文字列として生成
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; padding: 40px; color: #333; }}
            .header {{ border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 30px; }}
            .title {{ font-size: 28px; font-weight: bold; }}
            .timestamp {{ color: #7f8c8d; float: right; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: right; }}
            th {{ background-color: #f8f9fa; font-weight: bold; }}
            .best-row {{ background-color: #e8f4fd; font-weight: bold; }}
            .chart-placeholder {{ border: 1px dashed #ccc; height: 300px; text-align: center; line-height: 300px; color: #999; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <span class="timestamp">生成日: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M')}</span>
            <div class="title">ガス料金改定シミュレーション 報告書</div>
        </div>
        <h3>1. 収支インパクト計</h3>
        {summ_df.to_html(index=False, classes='table')}
        <p>※本レポートを右クリック→「印刷」からPDFとして保存してください。</p>
    </body>
    </html>
    """
    b64 = base64.b64encode(html.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" target="_blank" style="text-decoration:none;"><button style="width:100%; height:40px; background-color:#e74c3c; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">📄 報告用PDFレポートを生成 (別窓)</button></a>'

# ---------------------------------------------------------
# 4. メインUI
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'], key="u")
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'], key="m")
    if file_master:
        df_master_all = smart_load_wrapper(file_master)
        u_ids = sorted(df_master_all['料金表番号'].unique())
        selected_ids = st.multiselect("対象料金表", u_ids, default=u_ids)

if file_usage and file_master:
    df_usage = smart_load_wrapper(file_usage)
    df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    
    t1, t2, t3 = st.tabs(["Design", "Simulation", "Analysis"])

    with t1:
        plan_tabs = st.tabs([f"Plan {i+1}" for i in range(5)])
        new_plans = {}
        for i, pt in enumerate(plan_tabs):
            with pt:
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.base_a[i] = st.number_input(f"🖋️ A区画 基本料金", value=st.session_state.base_a[i], key=f"ba_{i}")
                    edited = st.data_editor(st.session_state.plan_data[i], use_container_width=True, key=f"ed_{i}")
                    st.session_state.plan_data[i] = edited
                with c2:
                    bases = calculate_slide_rates(st.session_state.base_a[i], edited)
                    res_df = pd.DataFrame([{"区画名":r['区画名'], "MAX":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']} for _, r in edited.iterrows()])
                    new_plans[f"Plan_{i+1}"] = res_df
                    st.dataframe(res_df.style.format({"MAX":"{:.1f}","基本料金":"{:,.2f}","単位料金":"{:,.4f}"}), hide_index=True)

    with t2:
        if st.button("🚀 計算実行", type="primary"):
            res = df_target_usage.copy()
            res['現行料金'] = res.apply(lambda r: calculate_bill_single(r['使用量'], df_master_all[df_master_all['料金表番号']==r['料金表番号']]), axis=1)
            for pn, pdf in new_plans.items():
                res[pn] = res.apply(lambda r: calculate_bill_single(r['使用量'], pdf), axis=1)
            st.session_state.simulation_result = res
        
        if st.session_state.simulation_result is not None:
            sr = st.session_state.simulation_result
            total_curr = sr['現行料金'].sum()
            summ_data = [{"プラン名": "現行", "売上": total_curr, "差額": 0}]
            for pn in new_plans.keys():
                t_new = sr[pn].sum()
                summ_data.append({"プラン名": pn, "売上": t_new, "差額": t_new - total_curr})
            
            summ_df = pd.DataFrame(summ_data)
            st.dataframe(summ_df.style.format({"売上":"¥{:,.0f}","差額":"¥{:,.0f}"}), use_container_width=True)
            
            st.markdown("---")
            c_ex, c_pdf = st.columns(2)
            with c_ex:
                output = io.BytesIO()
                summ_df.to_excel(output, index=False)
                st.download_button("📊 Excel保存", data=output.getvalue(), file_name="report.xlsx", use_container_width=True)
            with c_pdf:
                # PDF(HTML)レポートボタン
                st.markdown(get_pdf_report_html(summ_df), unsafe_allow_html=True)

    with t3:
        st.info("Analysis tab ready.")
else:
    st.info("👈 CSVを読み込んでください")

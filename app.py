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
# 1. 設定 & デザイン (Gasio Style 完全維持)
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
st.markdown('<div class="sub-title">Cloud Edition - Simulation System</div>', unsafe_allow_html=True)

# ステート管理
if 'simulation_result' not in st.session_state: st.session_state.simulation_result = None
if 'plan_data' not in st.session_state:
    d_df = pd.DataFrame({'No': [1, 2, 3], '区画名': ['A', 'B', 'C'], '適用上限(m3)': [8.0, 30.0, 99999.0], '単位料金': [500.0, 400.0, 300.0]})
    st.session_state.plan_data = {i: d_df.copy() for i in range(5)}
    st.session_state.base_a = {i: 1500.0 for i in range(5)}

CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
COLOR_BAR, COLOR_CURRENT, COLOR_NEW = '#34495e', '#95a5a6', '#e67e22'

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {'基本':'基本料金','基礎料金':'基本料金','Base':'基本料金','上限':'MAX','適用上限':'MAX','ID':'料金表番号','Usage':'使用量','調定':'調定数'}
    df = df.rename(columns=rename_map)
    for c in ['使用量', 'MAX', '調定数']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0 if c!='MAX' else 999999999.0)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    return df

def smart_load_wrapper(file, file_type='generic'):
    # RateMakeロジック含む
    for enc in ['cp932', 'utf-8', 'shift_jis']:
        try:
            file.seek(0); df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

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

def get_tier_name(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    df = tariff_df.copy()
    if '適用上限(m3)' in df.columns: df = df.rename(columns={'適用上限(m3)':'MAX'})
    df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    sorted_df = df.sort_values('MAX').reset_index(drop=True)
    applicable = sorted_df[sorted_df['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_df.iloc[-1]
    return str(row.get('区画名', row.get('区画', row.name + 1)))

# ---------------------------------------------------------
# 3. 報告用レポート生成
# ---------------------------------------------------------
def get_pdf_report_html(summ_df, sel_plan_name):
    formatted_table = summ_df.style.format({"売上総額": "¥{:,.0f}", "差額": "¥{:,.0f}", "増減率": "{:+.2f}%"}).to_html(index=False)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja"><head><meta charset="UTF-8"><style>
    body {{ font-family: sans-serif; padding: 50px; color: #2c3e50; }}
    .report-header {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #dee2e6; padding: 10px; text-align: right; }}
    th {{ background-color: #f8f9fa; }}
    </style></head><body>
    <div class="report-header"><h1>料金改定シミュレーション報告書</h1></div>
    <p>対象プラン: {sel_plan_name}</p>
    {formatted_table}
    <div style="margin-top:30px;"><button onclick="window.print()" style="padding:10px; background:#3498db; color:#fff; border:none; border-radius:4px;">PDF保存 / 印刷</button></div>
    </body></html>"""
    b64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    return f'<a href="data:text/html;charset=utf-8;base64,{b64}" target="_blank"><button style="width:100%; height:40px; background:#3498db; color:#fff; border:none; border-radius:4px; font-weight:bold;">📄 報告用レポートを生成</button></a>'

# ---------------------------------------------------------
# 4. メインUI
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    uploaded_config = st.file_uploader("📂 設定復元 (.json)", type=['json'], key="cfg")
    if uploaded_config:
        data = json.load(uploaded_config)
        st.session_state.plan_data = {int(k): pd.DataFrame(v) for k, v in data['plan_data'].items()}
        st.session_state.base_a = {int(k): v for k, v in data['base_a'].items()}
    
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'], key="u")
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'], key="m")
    
    if file_master:
        df_master_all = smart_load_wrapper(file_master, 'master')
        if df_master_all is not None:
            u_ids = sorted(df_master_all['料金表番号'].unique())
            selected_ids = st.multiselect("対象料金表", u_ids, default=u_ids)

    st.markdown("---")
    save_json_data = json.dumps({'plan_data': {k: v.to_dict(orient='records') for k, v in st.session_state.plan_data.items()}, 'base_a': st.session_state.base_a}, indent=2, ensure_ascii=False)
    st.download_button("💾 設定保存(.json)", save_json_data, f"gasio_config_{datetime.datetime.now().strftime('%Y%m%d')}.json")

if file_usage and file_master and 'selected_ids' in locals():
    df_usage = smart_load_wrapper(file_usage, 'usage')
    df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    
    t_des, t_sim, t_ana = st.tabs(["Design", "Simulation", "Analysis"])

    with t_des:
        plan_tabs = st.tabs([f"Plan {i+1}" for i in range(5)])
        new_plans = {}
        for i, pt in enumerate(plan_tabs):
            with pt:
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.base_a[i] = st.number_input(f"🖋️ A区画 基本料金", value=st.session_state.base_a[i], key=f"ba_{i}", format="%.2f")
                    edited = st.data_editor(st.session_state.plan_data[i], use_container_width=True, key=f"ed_{i}")
                    st.session_state.plan_data[i] = edited
                with c2:
                    if not edited.empty:
                        bases = calculate_slide_rates(st.session_state.base_a[i], edited)
                        res_df = pd.DataFrame([{"区画名":r['区画名'], "MAX":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']} for _, r in edited.iterrows()])
                        new_plans[f"Plan_{i+1}"] = res_df
                        st.dataframe(res_df.style.format({"MAX":"{:.1f}","基本料金":"{:,.2f}","単位料金":"{:,.4f}"}), hide_index=True)

    with t_sim:
        st.markdown("##### 収支影響シミュレーション")
        if st.button("🚀 計算実行", type="primary"):
            res = df_target_usage.copy()
            res['現行料金'] = res.apply(lambda r: calculate_bill_single(r['使用量'], df_master_all[df_master_all['料金表番号']==r['料金表番号']]), axis=1)
            for pn, pdf in new_plans.items():
                res[pn] = res.apply(lambda r: calculate_bill_single(r['使用量'], pdf), axis=1)
                res[f"{pn}_差額"] = res[pn] - res['現行料金']
            st.session_state.simulation_result = res
        
        if st.session_state.simulation_result is not None:
            sr = st.session_state.simulation_result
            total_curr = sr['現行料金'].sum()
            summ_list = [{"プラン名": "現行", "売上総額": total_curr, "差額": 0, "増減率": 0.0}]
            for pn in new_plans.keys():
                t_new = sr[pn].sum(); diff = t_new - total_curr; ratio = (diff/total_curr*100) if total_curr else 0
                summ_list.append({"プラン名": pn, "売上総額": t_new, "差額": diff, "増減率": ratio})
            
            st.markdown("---")
            st.subheader("📄 レポート出力")
            c_ex, c_pdf = st.columns(2)
            with c_ex:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    pd.DataFrame(summ_list).to_excel(writer, index=False, sheet_name='Summary')
                st.download_button("📊 Excel保存", data=output.getvalue(), file_name="gasio_report.xlsx", use_container_width=True)
            with c_pdf:
                st.markdown(get_pdf_report_html(pd.DataFrame(summ_list), "Plan_1"), unsafe_allow_html=True)

    with t_ana:
        st.markdown("##### 需要構成分析")
        sel_p = st.selectbox("比較対象", list(new_plans.keys()), key="s_p_a")
        
        # 【復旧】境界指紋チェック
        fps = {}
        for tid in selected_ids:
            m_sub = df_master_all[df_master_all['料金表番号'] == tid].sort_values('MAX')
            if not m_sub.empty:
                f = list(sorted(m_sub['MAX'].unique())); f[-1] = 999999999.0
                fps[tid] = tuple(f)
        ids_consistent = (len(set(fps.values())) <= 1)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Current: 現行構成**")
            if ids_consistent:
                m_rep = df_master_all[df_master_all['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
                df_target_usage['現行区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, m_rep))
                agg_c = df_target_usage.groupby('現行区画').agg(件数=('調定数','sum'), 使用量=('使用量','sum')).reset_index()
                st.plotly_chart(px.pie(agg_c, values='件数', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
            else:
                st.info("⚠️ 境界不一致のためヒストグラムを表示")
                st.plotly_chart(px.histogram(df_target_usage, x="使用量", color="料金表番号", nbins=50), use_container_width=True)
        with g2:
            st.markdown(f"**Proposal: {sel_p}構成**")
            df_target_usage['新区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, new_plans[sel_p]))
            agg_n = df_target_usage.groupby('新区画').agg(件数=('調定数','sum'), 使用量=('使用量','sum')).reset_index()
            st.plotly_chart(px.pie(agg_n, values='件数', names='新区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
else:
    st.info("👈 CSVを読み込んでください")

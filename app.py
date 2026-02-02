import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import json
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Style 完全維持)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    
    /* メトリクス見切れ防止 */
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; overflow-wrap: break-word; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }

    /* イエローペン・スタイル：編集可能セルの右端に黄色のアクセント */
    [data-testid="stDataEditor"] div[data-testid="stTable"] td[aria-readonly="false"] {
        border-right: 5px solid #fdd835 !important;
        background-color: #fffde7 !important;
    }

    .stMetric {
        background-color: #fdfdfd;
        padding: 10px 15px;
        border-radius: 6px;
        border-left: 5px solid #3498db;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div.stButton > button { font-weight: bold; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 計算機</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cloud Edition - Rate Simulation System</div>', unsafe_allow_html=True)

# --- ステート管理 ---
if 'simulation_result' not in st.session_state: st.session_state.simulation_result = None
if 'plan_data' not in st.session_state:
    d_df = pd.DataFrame({'No': [1, 2, 3], '区画名': ['A', 'B', 'C'], '適用上限(m3)': [8.0, 30.0, 99999.0], '単位料金': [500.0, 400.0, 300.0]})
    st.session_state.plan_data = {i: d_df.copy() for i in range(5)}
    st.session_state.base_a = {i: 1500.0 for i in range(5)}

CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
COLOR_BAR, COLOR_CURRENT, COLOR_NEW = '#34495e', '#95a5a6', '#e67e22'

# ---------------------------------------------------------
# 2. 関数定義 (実務ロジック完全復旧)
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {'基本':'基本料金','基礎料金':'基本料金','Base':'基本料金','上限':'MAX','適用上限':'MAX','ID':'料金表番号','Usage':'使用量','調定':'調定数'}
    df = df.rename(columns=rename_map)
    for c in ['使用量', 'MAX', '調定数']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0 if c!='MAX' else 999999999.0)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    return df

def load_ratemake_format(file, extract_type='master'):
    file.seek(0)
    content = file.getvalue()
    try: text = content.decode('cp932'); encoding = 'cp932'
    except: text = content.decode('utf-8', errors='ignore'); encoding = 'utf-8'
    lines = text.split('\n')
    if extract_type == 'master':
        header_idx = -1
        for i, line in enumerate(lines):
            if "調整単位" in line or "旧料金表" in line: header_idx = i; break
        if header_idx == -1: return None 
        file.seek(0)
        try:
            df_raw = pd.read_csv(file, header=header_idx, encoding=encoding)
            unit_col = [c for c in df_raw.columns if "調整単位" in str(c)]
            if not unit_col: return None
            u_idx = df_raw.columns.get_loc(unit_col[0])
            master_rows = []
            for i in range(len(df_raw)):
                row = df_raw.iloc[i]
                if pd.isna(row.iloc[u_idx]): break
                master_rows.append(row.iloc[[u_idx-3, u_idx-2, u_idx-1, u_idx]].values)
            df_m = pd.DataFrame(master_rows, columns=['MIN', 'MAX', '基本料金', '単位料金'])
            df_m['料金表番号'] = 10; df_m['区画'] = ['A','B','C','D','E'][:len(df_m)]
            return df_m.astype(float)
        except: return None
    return None

def smart_load_wrapper(file, file_type='generic'):
    df_rm = load_ratemake_format(file, extract_type=file_type)
    if df_rm is not None: return df_rm
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
# 3. サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    uploaded_config = st.file_uploader("📂 設定復元 (.json)", type=['json'], key="cfg")
    if uploaded_config:
        try:
            data = json.load(uploaded_config)
            st.session_state.plan_data = {int(k): pd.DataFrame(v) for k, v in data['plan_data'].items()}
            st.session_state.base_a = {int(k): v for k, v in data['base_a'].items()}
            st.success("復元しました")
        except: st.error("復元エラー")
    
    st.markdown("---")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'], key="u")
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'], key="m")
    
    selected_ids = []
    if file_master:
        df_master_all = smart_load_wrapper(file_master, 'master')
        if df_master_all is not None:
            u_ids = sorted(df_master_all['料金表番号'].unique())
            selected_ids = st.multiselect("対象料金表", u_ids, default=u_ids)

    st.markdown("---")
    save_json_data = json.dumps({'plan_data': {k: v.to_dict(orient='records') for k, v in st.session_state.plan_data.items()}, 'base_a': st.session_state.base_a}, indent=2, ensure_ascii=False)
    st.download_button("💾 設定保存(.json)", save_json_data, f"gasio_config_{datetime.datetime.now().strftime('%Y%m%d')}.json")

# ---------------------------------------------------------
# 4. メインエリア
# ---------------------------------------------------------
if file_usage and file_master and selected_ids:
    df_usage = smart_load_wrapper(file_usage, 'usage')
    df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    
    tab_design, tab_sim, tab_analysis = st.tabs(["Design", "Simulation", "Analysis"])

    with tab_design:
        st.markdown("##### 料金プラン設計")
        plan_tabs = st.tabs([f"Plan {i+1}" for i in range(5)])
        new_plans = {}
        for i, pt in enumerate(plan_tabs):
            with pt:
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.base_a[i] = st.number_input(f"🖋️ A区画 基本料金", value=st.session_state.base_a[i], key=f"ba_{i}", format="%.2f")
                    bc1, bc2, _ = st.columns([1,1,4])
                    if bc1.button("＋", key=f"add_{i}"):
                        curr = st.session_state.plan_data[i]
                        new_no = len(curr)+1
                        st.session_state.plan_data[i] = pd.concat([curr, pd.DataFrame({'No':[new_no], '区画名':["ABCDEFGHIJKLMNOPQRSTUVWXYZ"[new_no-1] if new_no<=26 else f"T{new_no}"], '適用上限(m3)':[99999.0], '単位料金':[max(0.0, curr.iloc[-1]['単位料金']-50.0)]})], ignore_index=True); st.rerun()
                    if bc2.button("－", key=f"del_{i}"):
                        if len(st.session_state.plan_data[i]) > 1:
                            st.session_state.plan_data[i] = st.session_state.plan_data[i].iloc[:-1].copy()
                            st.session_state.plan_data[i].iloc[-1, 2] = 99999.0; st.rerun()
                    
                    edited = st.data_editor(st.session_state.plan_data[i], use_container_width=True, key=f"ed_{i}", 
                                           column_config={"No": st.column_config.NumberColumn(disabled=True), "区画名": st.column_config.TextColumn("🖋️ 区画名"), "適用上限(m3)": st.column_config.NumberColumn("🖋️ 適用上限", format="%.1f"), "単位料金": st.column_config.NumberColumn("🖋️ 単位料金", format="%.4f")})
                    st.session_state.plan_data[i] = edited
                with c2:
                    if not edited.empty:
                        bases = calculate_slide_rates(st.session_state.base_a[i], edited)
                        res_df = pd.DataFrame([{"区画名":r['区画名'], "MIN":0.0, "MAX":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']} for _, r in edited.iterrows()])
                        new_plans[f"Plan_{i+1}"] = res_df
                        st.dataframe(res_df.style.format({"MIN": "{:,.1f}", "MAX": "{:,.1f}", "基本料金": "{:,.2f}", "単位料金": "{:,.4f}"}), hide_index=True, use_container_width=True)
                        st.plotly_chart(px.line(x=list(range(0, 51, 2)), y=[calculate_bill_single(v, res_df) for v in range(0, 51, 2)], height=250), use_container_width=True, key=f"pl_{i}")

    with tab_sim:
        st.markdown("##### 収支影響シミュレーション")
        if st.button("🚀 計算実行", type="primary"):
            with st.spinner("Calculating..."):
                res = df_target_usage.copy()
                res['現行料金'] = res.apply(lambda r: calculate_bill_single(r['使用量'], df_master_all[df_master_all['料金表番号']==r['料金表番号']], r['調定数']), axis=1)
                for pn, pdf in new_plans.items():
                    res[pn] = res.apply(lambda r: calculate_bill_single(r['使用量'], pdf, r['調定数']), axis=1)
                    res[f"{pn}_差額"] = res[pn] - res['現行料金']
                st.session_state.simulation_result = res
        
        if st.session_state.simulation_result is not None:
            sr = st.session_state.simulation_result
            total_curr = sr['現行料金'].sum()
            m_cols = st.columns(len(new_plans) + 1)
            m_cols[0].metric("現行 売上", f"¥{total_curr:,.0f}")
            summ_list = [{"プラン名": "現行", "売上総額": total_curr, "差額": 0, "増減率": 0.0}]
            for idx, pn in enumerate(new_plans.keys()):
                t_new = sr[pn].sum(); diff = t_new - total_curr; ratio = (diff/total_curr*100) if total_curr else 0
                summ_list.append({"プラン名": pn, "売上総額": t_new, "差額": diff, "増減率": ratio})
                m_cols[idx+1].metric(f"{pn}", f"¥{t_new:,.0f}", f"{ratio:+.2f}%")
            
            st.markdown("---")
            gc1, gc2 = st.columns(2)
            sel_p = gc1.selectbox("詳細分析プランを選択", list(new_plans.keys()), key="s_p_g")
            with gc1: st.plotly_chart(px.histogram(sr, x=f"{sel_p}_差額", nbins=50, title="影響額分布", color_discrete_sequence=[COLOR_NEW]), use_container_width=True)
            with gc2: st.plotly_chart(px.scatter(sr.sample(min(len(sr),1000)), x='使用量', y=['現行料金', sel_p], title="新旧料金プロット(1000件)", opacity=0.6), use_container_width=True)
            st.dataframe(pd.DataFrame(summ_list).style.format({"売上総額":"¥{:,.0f}","差額":"¥{:,.0f}","増減率":"{:.2f}%"}), hide_index=True, use_container_width=True)

    with tab_analysis:
        st.markdown("##### 需要構成分析")
        sel_p = st.selectbox("比較対象", list(new_plans.keys()), key="s_p_a")
        # 混在自動検知ロジック
        fps = {tid: tuple(sorted(df_master_all[df_master_all['料金表番号']==tid]['MAX'].unique())) for tid in selected_ids}
        for tid in fps: 
            l = list(fps[tid]); l[-1] = 999999999.0; fps[tid] = tuple(l)
        ids_consistent = (len(set(fps.values())) <= 1)
        
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Current: 現行構成**")
            if ids_consistent:
                m_rep = df_master_all[df_master_all['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
                df_target_usage['現行区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, m_rep))
                agg_c = df_target_usage.groupby('現行区画').agg(件数=('調定数','sum'), 使用量=('使用量','sum')).reset_index()
                st.plotly_chart(px.pie(agg_c, values='件数', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
                st.dataframe(agg_c.style.format({"使用量":"{:,.1f}"}), hide_index=True, use_container_width=True)
            else:
                st.info("⚠️ 複数の料金表が混在しているため、分布図をを表示")
                st.plotly_chart(px.histogram(df_target_usage, x="使用量", color="料金表番号", nbins=50, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
        with g2:
            st.markdown(f"**Proposal: {sel_p}構成**")
            df_target_usage['新区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, new_plans[sel_p]))
            agg_n = df_target_usage.groupby('新区画').agg(件数=('調定数','sum'), 使用量=('使用量','sum')).reset_index()
            st.plotly_chart(px.pie(agg_n, values='件数', names='新区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
            st.dataframe(agg_n.style.format({"件数":"{:,.0f}", "使用量":"{:,.1f}"}), hide_index=True, use_container_width=True)
else:
    st.info("👈 サイドバーからCSVを読み込んでください")

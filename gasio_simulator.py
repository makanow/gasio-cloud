import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import json
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; overflow-wrap: break-word; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }

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
    st.session_state.plan_data = {i: d_df.copy() for i in range(3)} 
    st.session_state.base_a = {i: 1500.0 for i in range(3)} 

CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
COLOR_BAR, COLOR_CURRENT, COLOR_NEW = '#34495e', '#95a5a6', '#e67e22'

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
# 【改良】3種類の料金表を含むリアルなサンプルデータ生成
def get_sample_usage_csv():
    df = pd.DataFrame({
        '料金表番号': [
            10, 10, 10, 10, 10,  # 一般想定
            20, 20, 20, 20, 20,  # 暖房想定
            30, 30, 30, 30, 30   # 大口想定
        ],
        '使用量': [
            5.2, 12.5, 28.0, 45.3, 3.0,
            18.5, 35.2, 60.1, 14.0, 42.8,
            55.0, 120.5, 80.2, 45.0, 210.0
        ]
    })
    return df.to_csv(index=False).encode('utf-8-sig')

def get_sample_master_csv():
    df = pd.DataFrame({
        '料金表番号': [10, 10, 10, 20, 20, 20, 30, 30],
        '区画名': ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B'],
        'MIN': [0, 8.0, 30.0, 0, 15.0, 50.0, 0, 50.0],
        'MAX': [8.0, 30.0, 99999.0, 15.0, 50.0, 99999.0, 50.0, 99999.0],
        '基本料金': [1800, 2600, 5600, 2000, 3000, 6000, 5000, 10000],
        '単位料金': [550, 450, 350, 500, 400, 300, 350, 250]
    })
    return df.to_csv(index=False).encode('utf-8-sig')

def normalize_columns(df):
    rename_map = {'基本':'基本料金','基礎料金':'基本料金','Base':'基本料金','上限':'MAX','適用上限':'MAX','ID':'料金表番号','Usage':'使用量'}
    df = df.rename(columns=rename_map)
    for c in ['使用量']: 
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    # カンマや通貨記号の除去処理
    for col in ['MIN', 'MAX', '基本料金', '単位料金']:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('￥', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if col == 'MAX':
                df[col] = df[col].fillna(999999999.0)
            else:
                df[col] = df[col].fillna(0.0)
                
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    
    # 調定数と取り付け数を完全に削除
    drop_cols = ['調定数', '取り付け数']
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    
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

def calculate_bill_single(usage, tariff_df):
    if tariff_df.empty: return 0
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
# 3. サイドバー & データロード
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    
    with st.expander("ℹ️ CSVインポートガイダンス", expanded=False):
        st.markdown("""
        **【1. 使用量CSV】**
        - `料金表番号` : 料金表マスタと照合するキー
        - `使用量`: 月間のガス使用量
        
        **【2. 料金表マスタCSV】**
        - `料金表番号` 
        - `MIN`, `MAX`: 各区画の適用範囲
        - `基本料金`, `単位料金`: 各区画の料金設定
        """)
        st.download_button("📥 使用量サンプルCSV", get_sample_usage_csv(), "sample_usage.csv", "text/csv")
        st.download_button("📥 マスタサンプルCSV", get_sample_master_csv(), "sample_master.csv", "text/csv")

    st.markdown("---")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'], key="u")
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'], key="m")
    
    # 🌟 データ読み込みとデモモードの判定
    df_master_all = None
    df_usage = None
    selected_ids = []
    is_demo_mode = True

    if file_master and file_usage:
        tmp_master = smart_load_wrapper(file_master, 'master')
        tmp_usage = smart_load_wrapper(file_usage, 'usage')
        if tmp_master is not None and tmp_usage is not None:
            df_master_all = tmp_master
            df_usage = tmp_usage
            is_demo_mode = False
            u_ids = sorted(df_master_all['料金表番号'].unique())
            selected_ids = st.multiselect("対象料金表", u_ids, default=u_ids)

    if is_demo_mode:
        st.info("💡 CSV未設定のため、デモデータ読込中")
        # 【改良】3種類の料金表を含むデモ用マスタ
        df_master_all = pd.DataFrame({
            '料金表番号': [10, 10, 10, 20, 20, 20, 30, 30],
            '区画名': ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B'],
            'MIN': [0.0, 8.0, 30.0, 0.0, 15.0, 50.0, 0.0, 50.0],
            'MAX': [8.0, 30.0, 99999.0, 15.0, 50.0, 99999.0, 50.0, 99999.0],
            '基本料金': [1800.0, 2600.0, 5600.0, 2000.0, 3000.0, 6000.0, 5000.0, 10000.0],
            '単位料金': [550.0, 450.0, 350.0, 500.0, 400.0, 300.0, 350.0, 250.0]
        })
        # 【改良】それぞれの料金表特性に合わせた使用量のばらつきをシミュレート
        np.random.seed(42)
        u10 = np.round(np.random.gamma(shape=2.5, scale=6.0, size=500), 1)
        u20 = np.round(np.random.gamma(shape=3.0, scale=10.0, size=200), 1)
        u30 = np.round(np.random.gamma(shape=5.0, scale=15.0, size=50), 1)
        
        df_usage = pd.DataFrame({
            '料金表番号': [10]*500 + [20]*200 + [30]*50,
            '使用量': np.concatenate([u10, u20, u30])
        })
        selected_ids = [10, 20, 30]

# ---------------------------------------------------------
# 4. メインエリア
# ---------------------------------------------------------
if df_usage is not None and df_master_all is not None and selected_ids:
    df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    
    if is_demo_mode:
        st.warning("🚀 **現在デモモードで動作中**：デモデータでシミュレーションしています。ご自身のデータを分析するには、左のサイドバーから「使用量CSV」と「マスタCSV」をアップロードしてください。")

    with st.expander("📋 現行の料金表マスタを確認する（比較用）", expanded=False):
        st.markdown("現在選択されている料金表マスタです。新しいプランを設計する際の基準としてご覧ください。")
        master_cols = st.columns(min(len(selected_ids), 3))
        for idx, t_id in enumerate(selected_ids):
            with master_cols[idx % 3]:
                st.markdown(f"**【料金表番号: {t_id}】**")
                target_df = df_master_all[df_master_all['料金表番号'] == t_id].copy()
                st.dataframe(
                    target_df[['MIN', 'MAX', '基本料金', '単位料金']].style.format({
                        "MIN": "{:,.1f}", "MAX": "{:,.1f}", "基本料金": "¥{:,.2f}", "単位料金": "¥{:,.2f}"
                    }), hide_index=True, use_container_width=True
                )

    tab_design, tab_sim, tab_analysis = st.tabs(["Design", "Simulation", "Analysis"])

    with tab_design:
        st.markdown("##### 📊 料金プラン一括比較 & 設計")
        new_plans = {}
        for i in range(3):
            if not st.session_state.plan_data[i].empty:
                curr_plan = st.session_state.plan_data[i]
                bases = calculate_slide_rates(st.session_state.base_a[i], curr_plan)
                res_df = pd.DataFrame([{"区画名":r['区画名'], "MIN":0.0, "MAX":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']} for _, r in curr_plan.iterrows()])
                new_plans[f"Plan_{i+1}"] = res_df

        sum_cols = st.columns(3)
        for i, (p_name, p_df) in enumerate(new_plans.items()):
            with sum_cols[i]:
                st.markdown(f"**{p_name}**")
                st.dataframe(p_df.style.format({"MIN": "{:,.1f}", "MAX": "{:,.1f}", "基本料金": "¥{:,.0f}", "単位料金": "¥{:,.2f}"}), hide_index=True, use_container_width=True)

        st.markdown("###### 📈 料金カーブ比較 (0〜50m3)")
        compare_df = pd.DataFrame({"使用量": list(range(0, 51, 2))})
        for p_name, p_df in new_plans.items():
            compare_df[p_name] = compare_df["使用量"].apply(lambda v: calculate_bill_single(v, p_df))
        
        fig = px.line(compare_df, x="使用量", y=list(new_plans.keys()), height=300, color_discrete_sequence=['#3498db', '#e74c3c', '#2ecc71'])
        fig.update_layout(yaxis_title="ガス料金(円)", legend_title="プラン", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("##### 🛠️ プラン詳細編集")
        plan_tabs = st.tabs([f"Plan {i+1}" for i in range(3)]) 
        for i, pt in enumerate(plan_tabs):
            with pt:
                c1, c2 = st.columns([1, 2]) 
                with c1:
                    st.session_state.base_a[i] = st.number_input(f"🖋️ A区画 基本料金", value=st.session_state.base_a[i], key=f"ba_{i}", format="%.2f")
                    bc1, bc2, _ = st.columns([1,1,2])
                    if bc1.button("＋ 区画追加", key=f"add_{i}"):
                        curr = st.session_state.plan_data[i]
                        new_no = len(curr)+1
                        st.session_state.plan_data[i] = pd.concat([curr, pd.DataFrame({'No':[new_no], '区画名':["ABCDEFGHIJKLMNOPQRSTUVWXYZ"[new_no-1] if new_no<=26 else f"T{new_no}"], '適用上限(m3)':[99999.0], '単位料金':[max(0.0, curr.iloc[-1]['単位料金']-50.0)]})], ignore_index=True)
                        st.rerun()
                    if bc2.button("－ 区画削除", key=f"del_{i}"):
                        if len(st.session_state.plan_data[i]) > 1:
                            st.session_state.plan_data[i] = st.session_state.plan_data[i].iloc[:-1].copy()
                            st.session_state.plan_data[i].iloc[-1, 2] = 99999.0
                            st.rerun()
                with c2:
                    edited = st.data_editor(st.session_state.plan_data[i], use_container_width=True, key=f"ed_plan_{i}", 
                                           column_config={"No": st.column_config.NumberColumn(disabled=True), "区画名": st.column_config.TextColumn("🖋️ 区画名"), "適用上限(m3)": st.column_config.NumberColumn("🖋️ 適用上限", format="%.1f"), "単位料金": st.column_config.NumberColumn("🖋️ 単位料金", format="%.4f")})
                    if not edited.equals(st.session_state.plan_data[i]):
                        st.session_state.plan_data[i] = edited
                        st.rerun()

    with tab_sim:
        st.markdown("##### 収支影響シミュレーション")
        if st.button("🚀 計算実行", key="calc_run", type="primary"):
            with st.spinner("Calculating..."):
                res = df_target_usage.copy()
                res['現行料金'] = res.apply(lambda r: calculate_bill_single(r['使用量'], df_master_all[df_master_all['料金表番号']==r['料金表番号']]), axis=1)
                for pn, pdf in new_plans.items():
                    res[pn] = res.apply(lambda r: calculate_bill_single(r['使用量'], pdf), axis=1)
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
            csv_result = sr.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="💾 シミュレーション結果をCSV出力",
                data=csv_result,
                file_name=f"sim_result_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

            st.markdown("---")
            gc1, gc2 = st.columns(2)
            sel_p = gc1.selectbox("詳細分析プランを選択", list(new_plans.keys()), key="s_p_g")
            with gc1: st.plotly_chart(px.histogram(sr, x=f"{sel_p}_差額", nbins=50, title="影響額分布", color_discrete_sequence=[COLOR_NEW]), use_container_width=True)
            with gc2: st.plotly_chart(px.scatter(sr.sample(min(len(sr),1000)), x='使用量', y=['現行料金', sel_p], title="新旧料金プロット(最大1000件)", opacity=0.6), use_container_width=True)
            st.dataframe(pd.DataFrame(summ_list).style.format({"売上総額":"¥{:,.0f}","差額":"¥{:,.0f}","増減率":"{:.2f}%"}), hide_index=True, use_container_width=True)

    with tab_analysis:
        st.markdown("##### 需要構成分析")
        sel_p = st.selectbox("比較対象", list(new_plans.keys()), key="s_p_a")
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
                agg_c = df_target_usage.groupby('現行区画').agg(件数=('使用量','count'), 使用量=('使用量','sum')).reset_index()
                st.plotly_chart(px.pie(agg_c, values='件数', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
                st.dataframe(agg_c.style.format({"使用量":"{:,.1f}"}), hide_index=True, use_container_width=True)
            else:
                st.info("⚠️ 異なる区画の料金表が混在しているため、分布図を表示")
                st.plotly_chart(px.histogram(df_target_usage, x="使用量", color="料金表番号", nbins=50, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
        with g2:
            st.markdown(f"**Proposal: {sel_p}構成**")
            df_target_usage['新区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, new_plans[sel_p]))
            agg_n = df_target_usage.groupby('新区画').agg(件数=('使用量','count'), 使用量=('使用量','sum')).reset_index()
            st.plotly_chart(px.pie(agg_n, values='件数', names='新区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True)
            st.dataframe(agg_n.style.format({"件数":"{:,.0f}", "使用量":"{:,.1f}"}), hide_index=True, use_container_width=True)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as npimport streamlit as st
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
st.set_page_config(
    page_title="Gasio計算機", 
    page_icon="🔥",
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; font-family: "Helvetica Neue", Arial, sans-serif; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; margin-top: -5px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    .stMetric { background-color: #fdfdfd; padding: 15px 20px; border-radius: 6px; border-left: 5px solid #3498db; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    div.stButton > button { font-weight: bold; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 計算機</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cloud Edition - Rate Simulation System</div>', unsafe_allow_html=True)

# --- ステート管理 ---
if 'simulation_result' not in st.session_state:
    st.session_state.simulation_result = None

if 'plan_data' not in st.session_state:
    default_df = pd.DataFrame({
        'No': [1, 2, 3],
        '区画名': ['A', 'B', 'C'],
        '適用上限(m3)': [8.0, 30.0, 99999.0],
        '単位料金': [500.0, 400.0, 300.0]
    })
    st.session_state.plan_data = {i: default_df.copy() for i in range(5)}
    st.session_state.base_a = {i: 1500.0 for i in range(5)}

CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
COLOR_BAR, COLOR_CURRENT, COLOR_NEW = '#34495e', '#95a5a6', '#e67e22'

# ---------------------------------------------------------
# 2. 関数定義 (オリジナル継承 + 統合ロジック)
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX', '下限': 'MIN', '適用下限': 'MIN',
        'ID': '料金表番号', 'Code': '料金表番号',
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量',
        '調定': '調定数', 'BillingCount': '調定数', 'Billable': '調定数',
        '取付': '取付数', 'MeterCount': '取付数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    if '取付数' not in df.columns: df['取付数'] = 1
    # 数値化ガード
    if '使用量' in df.columns: df['使用量'] = pd.to_numeric(df['使用量'], errors='coerce').fillna(0.0)
    if 'MAX' in df.columns: df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    return df

def smart_load_wrapper(file, file_type='generic'):
    df_ratemake = load_ratemake_format(file, extract_type=file_type)
    if df_ratemake is not None: return df_ratemake
    for enc in ['cp932', 'utf-8', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

def load_ratemake_format(file, extract_type='master'):
    file.seek(0)
    content = file.getvalue()
    try: text = content.decode('cp932'); encoding = 'cp932'
    except:
        try: text = content.decode('utf-8', errors='ignore'); encoding = 'utf-8'
        except: return None
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
                if len(master_rows) >= 10: break # 安全弁
            df_m = pd.DataFrame(master_rows, columns=['MIN', 'MAX', '基本料金', '単位料金'])
            df_m['料金表番号'] = 10; df_m['区画'] = ['A','B','C','D','E','F','G','H','I','J'][:len(df_m)]
            return df_m.astype(float)
        except: return None
    elif extract_type == 'usage':
        # (オリジナル usage 抽出ロジック維持)
        header_idx = -1
        for i, line in enumerate(lines):
            if "需要群名" in line and "延調定数比率" in line: header_idx = i; break
        if header_idx == -1: return None
        file.seek(0)
        try:
            df_raw = pd.read_csv(file, header=header_idx, encoding=encoding)
            name_col = [c for c in df_raw.columns if "需要群名" in str(c)][0]
            count_col = [c for c in df_raw.columns if "年間調定数" in str(c)][0]
            vol_col = [c for c in df_raw.columns if "年間販売量" in str(c)][0]
            customers = []
            cid = 1
            for i in range(len(df_raw)):
                row = df_raw.iloc[i]
                if pd.isna(row[name_col]) or "合計" in str(row[name_col]): break
                count = int(float(row[count_col])) if pd.notna(row[count_col]) else 0
                vol = float(row[vol_col]) if pd.notna(row[vol_col]) else 0
                if count <= 0: continue
                avg = vol/count; sigma = avg*0.2
                usages = np.maximum(np.random.normal(avg, sigma, count), 0.1)
                if usages.sum() > 0: usages = usages * (vol/usages.sum())
                for u in usages:
                    customers.append({'顧客ID': f"C{cid:05d}", '料金表番号': 10, '使用量': u, '調定数': 1, '取付数': 1})
                    cid += 1
            return pd.DataFrame(customers)
        except: return None

def get_tier_name(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    df = tariff_df.copy()
    if '適用上限(m3)' in df.columns: df = df.rename(columns={'適用上限(m3)': 'MAX'})
    if 'MAX' not in df.columns: return "Unknown"
    df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    sorted_df = df.sort_values('MAX').reset_index(drop=True)
    applicable = sorted_df[sorted_df['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_df.iloc[-1]
    for col in ['区画', '区画名']:
        if col in row.index and pd.notna(row[col]): return str(row[col])
    rank = row.name + 1
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return f"{letters[rank-1] if rank <= 26 else rank} ({row.get('MIN',0):.0f}〜{row['MAX']:.0f})"

def calculate_slide_rates(base_a, blocks_df):
    blocks = blocks_df.copy().sort_values('No')
    base_fees = {blocks.iloc[0]['No']: base_a}
    for i in range(1, len(blocks)):
        prev, curr = blocks.iloc[i-1], blocks.iloc[i]
        base_fees[curr['No']] = base_fees[prev['No']] + (prev['単位料金'] - curr['単位料金']) * prev['適用上限(m3)']
    return base_fees

def calculate_bill_single(usage, tariff_df, billing_count=1):
    if billing_count == 0 or tariff_df.empty: return 0
    df = tariff_df.copy()
    if '適用上限(m3)' in df.columns: df = df.rename(columns={'適用上限(m3)': 'MAX'})
    df['MAX'] = pd.to_numeric(df['MAX'], errors='coerce').fillna(999999999.0)
    target = df[df['MAX'] >= (usage - 1e-9)].sort_values('MAX')
    row = target.iloc[0] if not target.empty else df.sort_values('MAX').iloc[-1]
    return int(row['基本料金'] + (usage * row['単位料金']))

# ---------------------------------------------------------
# 3. サイドバー (インポート機能復旧)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    uploaded_config = st.file_uploader("📂 設定復元 (.json)", type=['json'], key="config_load")
    if uploaded_config:
        try:
            data = json.load(uploaded_config)
            if 'plan_data' in data: st.session_state.plan_data = {int(k): pd.DataFrame(v) for k, v in data['plan_data'].items()}
            if 'base_a' in data: st.session_state.base_a = {int(k): v for k, v in data['base_a'].items()}
            st.success("設定を復元しました")
        except: st.error("復元エラー")
    
    st.markdown("---")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'], key="usage")
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'], key="master")

    selected_ids = []
    if file_master:
        df_master_all = smart_load_wrapper(file_master, 'master')
        if df_master_all is not None:
            u_ids = sorted(df_master_all['料金表番号'].unique())
            st.markdown("##### ⚙️ Target IDs")
            selected_ids = st.multiselect("対象料金表", u_ids, default=u_ids)
            # 移植：指紋チェック
            fps = {}
            for tid in selected_ids:
                m_sub = df_master_all[df_master_all['料金表番号'] == tid].sort_values('MAX')
                if not m_sub.empty:
                    f = sorted(m_sub['MAX'].unique()); f[-1] = 999999999.0
                    fps[tid] = tuple(f)
            if selected_ids and len(set(fps.values())) > 1:
                st.error("⚠️ 境界線不一致。合算分析不可。")
                selected_ids_valid = False
            else:
                selected_ids_valid = True

    if st.button("💾 設定保存 (.json)"):
        save_data = {'plan_data': {k: v.to_dict(orient='records') for k, v in st.session_state.plan_data.items()}, 'base_a': st.session_state.base_a}
        st.download_button("Download JSON", json.dumps(save_data, indent=2, ensure_ascii=False), f"gasio_config_{datetime.datetime.now().strftime('%Y%m%d')}.json")

# ---------------------------------------------------------
# 4. メイン
# ---------------------------------------------------------
if file_usage and file_master and selected_ids:
    df_usage = smart_load_wrapper(file_usage, 'usage')
    if df_usage is None or df_master_all is None: st.error("データ読込エラー"); st.stop()
    df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    
    st.success(f"✅ Gasio Ready: {len(df_target_usage):,} 件")
    tab1, tab2, tab3 = st.tabs(["Design", "Simulation", "Analysis"])

    with tab1:
        plan_tabs = st.tabs([f"Plan {i+1}" for i in range(5)])
        new_plans = {}
        for i, pt in enumerate(plan_tabs):
            with pt:
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.base_a[i] = st.number_input(f"A区画 基本料金", value=st.session_state.base_a[i], key=f"ba_{i}")
                    # (編集ボタン等のUIはオリジナル通り)
                    edited = st.data_editor(st.session_state.plan_data[i], use_container_width=True, key=f"ed_{i}")
                    st.session_state.plan_data[i] = edited
                with c2:
                    if not edited.empty:
                        bases = calculate_slide_rates(st.session_state.base_a[i], edited)
                        res = []
                        p_max = 0
                        for _, r in edited.sort_values('No').iterrows():
                            res.append({"区画":r['区画名'], "MIN":p_max, "MAX":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']})
                            p_max = r['適用上限(m3)']
                        res_df = pd.DataFrame(res)
                        new_plans[f"Plan_{i+1}"] = res_df
                        st.dataframe(res_df.style.format("{:.2f}"), use_container_width=True)

    with tab2:
        if st.button("🚀 計算実行 (Run Simulation)", type="primary"):
            res = df_target_usage.copy()
            res['現行料金'] = res.apply(lambda r: calculate_bill_single(r['使用量'], df_master_all[df_master_all['料金表番号']==r['料金表番号']], r['調定数']), axis=1)
            for pn, pdf in new_plans.items():
                res[pn] = res.apply(lambda r: calculate_bill_single(r['使用量'], pdf, r['調定数']), axis=1)
            st.session_state.simulation_result = res
        
        if st.session_state.simulation_result is not None:
            st.dataframe(st.session_state.simulation_result.head())

    with tab3:
        st.markdown("##### 需要構成分析")
        if selected_ids_valid:
            master_rep = df_master_all[df_master_all['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
            df_target_usage['現行区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, master_rep))
            agg_c = df_target_usage.groupby('現行区画').agg(調定数=('調定数','sum'), 使用量=('使用量','sum')).reset_index()
            
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.pie(agg_c, values='調定数', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="調定数シェア"), use_container_width=True)
            c2.plotly_chart(px.pie(agg_c, values='使用量', names='現行区画', hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS, title="使用量シェア"), use_container_width=True)
            st.dataframe(agg_c, use_container_width=True, hide_index=True)
        else:
            st.warning("境界不一致のためヒストグラムを表示")
            st.plotly_chart(px.histogram(df_target_usage, x="使用量", color="料金表番号"), use_container_width=True)
import io
import json
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン (Gasio Style)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gasio計算機", 
    page_icon="🔥",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# カスタムCSS (Gasio Brand Colors)
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif;
    }
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        color: #2c3e50;
        margin-bottom: 0px;
        letter-spacing: -1px;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #7f8c8d;
        margin-top: -5px;
        margin-bottom: 20px;
        border-bottom: 2px solid #3498db; /* Gasio Blue */
        padding-bottom: 10px;
    }
    .stMetric {
        background-color: #fdfdfd;
        padding: 15px 20px;
        border-radius: 6px;
        border-left: 5px solid #3498db;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div.stButton > button {
        font-weight: bold;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# ヘッダー (Logo Coloring)
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    # Gas(濃紺) i(赤) o(青)
    st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> 計算機</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cloud Edition - Rate Simulation System</div>', unsafe_allow_html=True)

# --- ステート管理 ---
if 'simulation_result' not in st.session_state:
    st.session_state.simulation_result = None

if 'plan_data' not in st.session_state:
    default_df = pd.DataFrame({
        'No': [1, 2, 3],
        '区画名': ['A', 'B', 'C'],
        '適用上限(m3)': [8.0, 30.0, 99999.0],
        '単位料金': [500.0000, 400.0000, 300.0000]
    })
    st.session_state.plan_data = {i: default_df.copy() for i in range(5)}
    st.session_state.base_a = {i: 1500.0 for i in range(5)}

# --- カラーパレット ---
CHIC_PIE_COLORS = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
COLOR_BAR = '#34495e'
COLOR_CURRENT = '#95a5a6'
COLOR_NEW = '#e67e22'

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------

def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX',
        '下限': 'MIN', '適用下限': 'MIN',
        'ID': '料金表番号', 'Code': '料金表番号',
        '調定': '調定数', 'BillingCount': '調定数', 'Billable': '調定数',
        '取付': '取付数', 'MeterCount': '取付数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    if '調定数' not in df.columns: df['調定数'] = 1
    if '取付数' not in df.columns: df['取付数'] = 1
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
            unit_col_idx = df_raw.columns.get_loc(unit_col[0])
            target_cols = [unit_col_idx-3, unit_col_idx-2, unit_col_idx-1, unit_col_idx]
            master_rows = []
            for i in range(len(df_raw)):
                row = df_raw.iloc[i]
                if pd.isna(row.iloc[unit_col_idx]): break
                master_rows.append(row.iloc[target_cols].values)
                if len(master_rows) >= 3: break 
            df_master = pd.DataFrame(master_rows, columns=['MIN', 'MAX', '基本料金', '単位料金'])
            df_master['料金表番号'] = 10
            df_master['区画'] = ['A', 'B', 'C', 'D', 'E'][:len(df_master)]
            return df_master.astype({'MIN': float, 'MAX': float, '基本料金': float, '単位料金': float})
        except: return None
    elif extract_type == 'usage':
        header_idx = -1
        for i, line in enumerate(lines):
            if "需要群名" in line and "延調定数比率" in line: header_idx = i; break
        if header_idx == -1: return None
        file.seek(0)
        try:
            df_raw = pd.read_csv(file, header=header_idx, encoding=encoding)
            name_col = [c for c in df_raw.columns if "需要群名" in str(c)][0]
            count_col = [c for c in df_raw.columns if "年間調定数" in str(c)][0]
            vol_col = [c for c in df_raw.columns if "年間販売量" in str(c)][0]
            customers = []
            cid = 1
            for i in range(len(df_raw)):
                row = df_raw.iloc[i]
                group_name = row[name_col]
                if pd.isna(group_name) or "合計" in str(group_name): break
                count = int(float(row[count_col])) if pd.notna(row[count_col]) else 0
                vol = float(row[vol_col]) if pd.notna(row[vol_col]) else 0
                if count <= 0: continue
                avg = vol / count; sigma = avg * 0.2
                usages = np.maximum(np.random.normal(avg, sigma, count), 0.1)
                if usages.sum() > 0: usages = usages * (vol / usages.sum())
                for u in usages:
                    customers.append({'顧客ID': f"C{cid:05d}", '料金表番号': 10, '使用量': u, '調定数': 1, '取付数': 1})
                    cid += 1
            return pd.DataFrame(customers)
        except: return None

def smart_load_wrapper(file, file_type='generic'):
    df_ratemake = load_ratemake_format(file, extract_type=file_type)
    if df_ratemake is not None: return df_ratemake
    file.seek(0)
    for enc in ['cp932', 'utf-8', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

def calculate_slide_rates(base_a, blocks_df):
    blocks = blocks_df.copy().sort_values('No')
    base_fees = {1: base_a}
    for i in range(2, len(blocks) + 2):
        prev = blocks[blocks['No'] == i-1]
        curr = blocks[blocks['No'] == i]
        if prev.empty or curr.empty: break
        limit = float(prev['適用上限(m3)'].iloc[0])
        p_unit = float(prev['単位料金'].iloc[0])
        c_unit = float(curr['単位料金'].iloc[0])
        base_fees[i] = base_fees[i-1] + (p_unit - c_unit) * limit
    return base_fees

def calculate_bill_single(usage, tariff_df, billing_count=1):
    if billing_count == 0: return 0
    if tariff_df.empty: return 0
    target = tariff_df.sort_values('MAX').loc[tariff_df.sort_values('MAX')['MAX'] >= usage]
    row = target.iloc[0] if not target.empty else tariff_df.sort_values('MAX').iloc[-1]
    return int(row['基本料金'] + (usage * row['単位料金']))

def get_tier_name(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    target = tariff_df.sort_values('MAX').loc[tariff_df.sort_values('MAX')['MAX'] >= usage]
    row = target.iloc[0] if not target.empty else tariff_df.sort_values('MAX').iloc[-1]
    for col in ['区画', '区画名']:
        if col in row.index and pd.notna(row[col]): return str(row[col])
    rank = tariff_df.sort_values('MAX').reset_index(drop=True).index.get_loc(row.name) + 1 if row.name in tariff_df.index else len(tariff_df)
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    label = letters[rank-1] if rank <= len(letters) else f"Tier{rank}"
    return f"{label} ({row['MIN']}〜{row['MAX']:.0f}m³)"

# ---------------------------------------------------------
# 3. サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    uploaded_config = st.file_uploader("📂 設定復元 (.json)", type=['json'], key="config_load")
    if uploaded_config:
        try:
            data = json.load(uploaded_config)
            if 'plan_data' in data: st.session_state.plan_data = {int(k): pd.DataFrame(v) for k, v in data['plan_data'].items()}
            if 'base_a' in data: st.session_state.base_a = {int(k): v for k, v in data['base_a'].items()}
            st.success("設定を復元しました")
        except: st.error("復元エラー")
    
    st.markdown("---")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'], key="usage")
    st.markdown("---")
    file_master = st.file_uploader("2. 料金表マスタCSV", type=['csv'], key="master")

    selected_ids = []
    if file_master:
        preview_master = smart_load_wrapper(file_master, 'master')
        if preview_master is not None:
            u_ids = sorted(preview_master['料金表番号'].unique())
            st.markdown("##### ⚙️ Simulation Target")
            selected_ids = st.multiselect("対象料金表", u_ids, default=u_ids)
            if selected_ids:
                with st.expander("選択された料金表プレビュー"):
                    for tid in selected_ids:
                        disp = preview_master[preview_master['料金表番号'] == tid].copy()
                        cols = [c for c in ['区画', '区画名', 'MIN', 'MAX', '基本料金', '単位料金'] if c in disp.columns]
                        st.dataframe(disp[cols].style.format({"MIN":"{:.1f}","MAX":"{:.1f}","基本料金":"{:.2f}","単位料金":"{:.2f}"}), hide_index=True, use_container_width=True)
    
    st.markdown("---")
    if st.button("💾 設定保存 (.json)"):
        save_data = {'plan_data': {k: v.to_dict(orient='records') for k, v in st.session_state.plan_data.items()}, 'base_a': st.session_state.base_a}
        st.download_button("Download JSON", json.dumps(save_data, indent=2, ensure_ascii=False), f"gasio_config_{datetime.datetime.now().strftime('%Y%m%d')}.json", "application/json")

# ---------------------------------------------------------
# 4. メインエリア
# ---------------------------------------------------------
if file_usage and file_master and selected_ids:
    df_usage = smart_load_wrapper(file_usage, 'usage')
    df_master = smart_load_wrapper(file_master, 'master')
    if df_usage is None or df_master is None: st.error("データ読込エラー"); st.stop()
    
    df_target_usage = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
    if df_target_usage.empty: st.warning("該当データなし"); st.stop()
    
    st.success(f"✅ Gasio Ready: 対象 {len(df_target_usage):,} 件")

    tab1, tab2, tab3 = st.tabs(["Design", "Simulation", "Analysis"])

    with tab1:
        st.markdown("##### 料金プラン設計")
        plan_tabs = st.tabs([f"Plan {i+1}" for i in range(5)])
        new_plans = {}
        for i, pt in enumerate(plan_tabs):
            with pt:
                c1, c2 = st.columns([1, 1])
                with c1:
                    base_a = st.number_input(f"A区画 基本料金", value=st.session_state.base_a[i], step=10.0, format="%.4f", key=f"base_a_{i}")
                    st.session_state.base_a[i] = base_a
                    bc1, bc2, _ = st.columns([1,1,4])
                    if bc1.button("＋", key=f"add_{i}"):
                        curr = st.session_state.plan_data[i]
                        new_no = len(curr)+1
                        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                        char = letters[new_no-1] if new_no<=len(letters) else f"T{new_no}"
                        st.session_state.plan_data[i] = pd.concat([curr, pd.DataFrame({'No':[new_no], '区画名':[char], '適用上限(m3)':[99999.0], '単位料金':[max(0, curr.iloc[-1]['単位料金']-50) if not curr.empty else 500]})], ignore_index=True)
                        st.rerun()
                    if bc2.button("－", key=f"del_{i}"):
                        if len(st.session_state.plan_data[i]) > 1:
                            st.session_state.plan_data[i] = st.session_state.plan_data[i].iloc[:-1].copy()
                            st.session_state.plan_data[i].iloc[-1, 2] = 99999.0
                            st.rerun()
                    
                    edited = st.data_editor(st.session_state.plan_data[i], num_rows="fixed", use_container_width=True, key=f"ed_{i}",
                        column_config={"No":st.column_config.NumberColumn(disabled=True, width=50), "区画名":st.column_config.TextColumn(width=80)})
                    if not edited.equals(st.session_state.plan_data[i]): st.session_state.plan_data[i] = edited

                with c2:
                    if not edited.empty:
                        bases = calculate_slide_rates(base_a, edited)
                        res = []
                        p_max = 0
                        for idx, r in edited.sort_values('No').iterrows():
                            res.append({"区画":r['区画名'], "MIN":p_max, "MAX":r['適用上限(m3)'], "基本料金":bases.get(r['No'],0), "単位料金":r['単位料金']})
                            p_max = r['適用上限(m3)']
                        res_df = pd.DataFrame(res)
                        new_plans[f"Plan_{i+1}"] = res_df
                        st.dataframe(res_df.style.format({"MIN":"{:.1f}","MAX":"{:.1f}","基本料金":"{:.4f}","単位料金":"{:.4f}"}), hide_index=True, use_container_width=True)
                        x = list(range(0, 51, 2)); y = [calculate_bill_single(v, res_df) for v in x]
                        fig = px.line(x=x, y=y, labels={'x':'使用量', 'y':'料金'}, height=250)
                        fig.update_traces(line_color=COLOR_BAR)
                        # 【修正】重複IDエラー回避のため、keyを付与
                        st.plotly_chart(fig, use_container_width=True, key=f"preview_chart_{i}")

    with tab2:
        st.markdown("##### 収支影響シミュレーション")
        if st.button("🚀 計算実行 (Run Simulation)", type="primary"):
            with st.spinner("Calculating..."):
                df_c = df_target_usage.copy()
                df_c['現行料金'] = df_c.apply(lambda r: calculate_bill_single(r['使用量'], df_master[df_master['料金表番号']==r['料金表番号']], r['調定数']), axis=1)
                for pn, pdf in new_plans.items():
                    df_c[pn] = df_c.apply(lambda r: calculate_bill_single(r['使用量'], pdf, r['調定数']), axis=1)
                    df_c[f"{pn}_差額"] = df_c[pn] - df_c['現行料金']
                st.session_state.simulation_result = df_c
        
        if st.session_state.simulation_result is not None:
            res = st.session_state.simulation_result
            total_curr = res['現行料金'].sum()
            summ = [{"プラン名":"現行 (Current)", "売上総額":total_curr, "増減額":0, "増減率":0}]
            for pn in new_plans:
                tn = res[pn].sum(); diff = tn - total_curr
                summ.append({"プラン名":pn, "売上総額":tn, "増減額":diff, "増減率":(diff/total_curr*100) if total_curr else 0})
            
            st.dataframe(pd.DataFrame(summ).style.format({"売上総額":"¥{:,.0f}", "増減額":"¥{:,.0f}", "増減率":"{:+.2f}%"}), hide_index=True, use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w:
                pd.DataFrame(summ).to_excel(w, sheet_name='Summary', index=False)
                res.to_excel(w, sheet_name='Detail', index=False)
            st.download_button("📊 結果ダウンロード (.xlsx)", buf.getvalue(), f"gasio_result_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            c1, c2 = st.columns(2)
            sel_p = c1.selectbox("プラン", list(new_plans.keys()))
            fig1 = px.histogram(res, x=f"{sel_p}_差額", nbins=50, title="差額分布", color_discrete_sequence=[COLOR_BAR])
            fig1.add_vline(x=0, line_dash="dash", line_color="red")
            # 【修正】固定キー付与
            c1.plotly_chart(fig1, use_container_width=True, key="sim_hist_chart")
            
            smp = res.sample(min(len(res), 1000))
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=smp['使用量'], y=smp['現行料金'], mode='markers', name='現行', marker=dict(color=COLOR_CURRENT, opacity=0.5)))
            fig2.add_trace(go.Scatter(x=smp['使用量'], y=smp[sel_p], mode='markers', name=sel_p, marker=dict(color=COLOR_NEW, opacity=0.5)))
            fig2.update_layout(title="新旧プロット比較", margin=dict(l=0,r=0,t=30,b=0))
            # 【修正】固定キー付与
            c2.plotly_chart(fig2, use_container_width=True, key="sim_scatter_chart")

    with tab3:
        st.markdown("##### 需要構成分析")
        c_sel, _ = st.columns([1,1])
        sel_new = c_sel.selectbox("比較対象プラン", list(new_plans.keys()) if new_plans else ["設定なし"])
        if sel_new != "設定なし":
            df_target_usage['現行区画'] = df_target_usage.apply(lambda r: get_tier_name(r['使用量'], df_master[df_master['料金表番号']==r['料金表番号']]), axis=1)
            df_target_usage['新プラン区画'] = df_target_usage['使用量'].apply(lambda x: get_tier_name(x, new_plans[sel_new]))
            
            g1, g2 = st.columns(2)
            with g1:
                st.markdown("**Current: 現行**")
                if len(selected_ids)==1:
                    agg_c = df_target_usage.groupby('現行区画').agg(調定数=('調定数','sum'), 総使用量=('使用量','sum')).reset_index().sort_values('現行区画')
                    sg1, sg2 = st.columns(2)
                    # 【修正】キー付与
                    sg1.plotly_chart(px.pie(agg_c, values='調定数', names='現行区画', title="調定数シェア", hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True, key="pie_curr_count")
                    sg2.plotly_chart(px.pie(agg_c, values='総使用量', names='現行区画', title="使用量シェア", hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True, key="pie_curr_vol")
                    st.dataframe(agg_c.style.format({"調定数":"{:,}", "総使用量":"{:,.1f}"}))
                else:
                    st.info("複数料金合算のため区画別シェアは非表示")
                    # 【修正】キー付与
                    st.plotly_chart(px.histogram(df_target_usage, x="使用量", color="料金表番号", nbins=50, title="全体使用量分布", color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True, key="hist_curr_dist")
            with g2:
                st.markdown(f"**Proposal: {sel_new}**")
                agg_n = df_target_usage.groupby('新プラン区画').agg(調定数=('調定数','sum'), 総使用量=('使用量','sum')).reset_index().sort_values('新プラン区画')
                sg1, sg2 = st.columns(2)
                # 【修正】キー付与
                sg1.plotly_chart(px.pie(agg_n, values='調定数', names='新プラン区画', title="調定数シェア", hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True, key="pie_new_count")
                sg2.plotly_chart(px.pie(agg_n, values='総使用量', names='新プラン区画', title="使用量シェア", hole=0.5, color_discrete_sequence=CHIC_PIE_COLORS), use_container_width=True, key="pie_new_vol")
                st.dataframe(agg_n.style.format({"調定数":"{:,}", "総使用量":"{:,.1f}"}))
else:
    st.info("👈 左側のサイドバーからデータを読み込んでください ")

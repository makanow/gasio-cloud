import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio mini", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    /* タイトルのフォントサイズとウェイト */
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; text-align: left; margin-bottom: 0; letter-spacing: -1px; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; text-align: left; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #f8f9fa; border-radius: 5px; padding: 10px; border-left: 4px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

# ロゴの文字色修復: i(赤), o(青)
st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> mini</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Current Status Visualizer (Stable Aggregation)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
# 【指示2】3種類の料金表を含むリアルなサンプルデータ生成
def get_sample_usage_csv():
    df = pd.DataFrame({
        '料金表番号': [10]*5 + [20]*5 + [30]*5,
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
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '適用上限': 'MAX', 'max': 'MAX',
        'ID': '料金表番号', 'Code': '料金表番号',
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' in df.columns:
        df['料金表番号'] = pd.to_numeric(df['料金表番号'], errors='coerce').fillna(0).astype(int)
    if '使用量' in df.columns:
        df['使用量'] = pd.to_numeric(df['使用量'], errors='coerce').fillna(0.0)
        
    # --- カンマや通貨記号の除去処理 ---
    for col in ['MIN', 'MAX', '基本料金', '単位料金']:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '', regex=False).str.replace('¥', '', regex=False).str.replace('￥', '', regex=False)
            if col == 'MAX':
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(999999999.0)
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
    # 【指示1】調定数と取り付け数を完全に削除
    drop_cols = ['調定', '調定数', 'BillingCount', '取付', '取付数']
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
                
    return df

def smart_load(file):
    for enc in ['utf-8', 'cp932', 'shift_jis']:
        try:
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            df.columns = df.columns.astype(str).str.strip()
            return normalize_columns(df)
        except: continue
    return None

def get_tier_name(usage, tariff_df):
    if tariff_df.empty: return "Unknown"
    sorted_df = tariff_df.sort_values('MAX').reset_index(drop=True)
    applicable = sorted_df[sorted_df['MAX'] >= (usage - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_df.iloc[-1]
    
    for col in ['区画名', '区画']:
        if col in row and pd.notna(row[col]): return str(row[col])
    
    rank = row.name + 1
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return letters[rank-1] if rank <= len(letters) else f"Tier{rank}"

# ---------------------------------------------------------
# 3. サイドバー: インポートガイダンス
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Import")
    
    # 【指示2】CSVインポートガイダンスの追加
    with st.expander("ℹ️ CSVインポートガイダンス", expanded=False):
        st.markdown("""
        **【1. 使用量CSV】**
        - `料金表番号`: マスタと照合するキー
        - `使用量`: 月間のガス使用量
        
        **【2. 料金表マスタCSV】**
        - `料金表番号`
        - `MIN`, `MAX`: 各区画の適用範囲
        - `基本料金`, `単位料金`: 各区画の料金設定
        """)
        st.download_button("📥 使用量サンプルCSV", get_sample_usage_csv(), "sample_usage.csv", "text/csv")
        st.download_button("📥 マスタサンプルCSV", get_sample_master_csv(), "sample_master.csv", "text/csv")
        
    st.markdown("---")
    file_usage = st.file_uploader("1. 使用量CSV", type=['csv'])
    file_master = st.file_uploader("2. 料金表マスタCSV ", type=['csv'])

# 🌟 データ読み込みとデモモードの判定
df_master = None
df_usage = None
is_demo_mode = True

if file_master and file_usage:
    tmp_master = smart_load(file_master)
    tmp_usage = smart_load(file_usage)
    if tmp_master is not None and tmp_usage is not None:
        df_master = tmp_master
        df_usage = tmp_usage
        is_demo_mode = False

if is_demo_mode:

    # 3種類の料金表マスタ
    df_master = pd.DataFrame({
        '料金表番号': [10, 10, 10, 20, 20, 20, 30, 30],
        '区画名': ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B'],
        'MIN': [0.0, 8.0, 30.0, 0.0, 15.0, 50.0, 0.0, 50.0],
        'MAX': [8.0, 30.0, 99999.0, 15.0, 50.0, 99999.0, 50.0, 99999.0],
        '基本料金': [1800.0, 2600.0, 5600.0, 2000.0, 3000.0, 6000.0, 5000.0, 10000.0],
        '単位料金': [550.0, 450.0, 350.0, 500.0, 400.0, 300.0, 350.0, 250.0]
    })
    # 使用量のシミュレート
    np.random.seed(42)
    u10 = np.round(np.random.gamma(shape=2.5, scale=6.0, size=500), 1)
    u20 = np.round(np.random.gamma(shape=3.0, scale=10.0, size=200), 1)
    u30 = np.round(np.random.gamma(shape=5.0, scale=15.0, size=50), 1)
    
    df_usage = pd.DataFrame({
        '料金表番号': [10]*500 + [20]*200 + [30]*50,
        '使用量': np.concatenate([u10, u20, u30])
    })

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if df_usage is not None and df_master is not None:
    if is_demo_mode:
        st.warning("🚀 **現在デモモードで動作中**：ご自身のデータを分析するには、左のサイドバーから「使用量CSV」と「マスタCSV」をアップロードしてください。")

    usage_ids = sorted(df_usage['料金表番号'].unique())
    
    # ⚠️ miniは区画不一致を許容しないため、デフォルトは先頭の1つ（例: 10）のみ選択状態にする
    selected_ids = st.sidebar.multiselect("料金表番号を選択", usage_ids, default=usage_ids[:1])

    if not selected_ids:
        st.stop()

    # === 現行マスタの確認エリア ===
    with st.expander("📋 現行の料金表マスタを確認する", expanded=False):
        st.markdown("現在選択されている料金表マスタです。")
        master_cols = st.columns(min(len(selected_ids), 3))
        for idx, t_id in enumerate(selected_ids):
            with master_cols[idx % 3]:
                st.markdown(f"**【料金表番号: {t_id}】**")
                target_df = df_master[df_master['料金表番号'] == t_id].copy()
                st.dataframe(
                    target_df[['MIN', 'MAX', '基本料金', '単位料金']].style.format({
                        "MIN": "{:,.1f}", "MAX": "{:,.1f}", "基本料金": "¥{:,.2f}", "単位料金": "¥{:,.2f}"
                    }), hide_index=True, use_container_width=True
                )

# 集計ロジック (全件・複数マスタ対応版)
    df_target = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()

    # 顧客1件ごとに、自身の「料金表番号」に該当するマスタを引いて区画名を判定する関数
    def apply_correct_tier(row):
        tid = row['料金表番号']
        usage = row['使用量']
        # その顧客の料金表番号専用のマスタを抽出
        t_master = df_master[df_master['料金表番号'] == tid]
        # 元々ある完璧な関数 get_tier_name に渡す
        return get_tier_name(usage, t_master)

    # iterrowsループの代わりにapplyを使って全行に一括適用（圧倒的に高速だ）
    df_target['Current_Tier'] = df_target.apply(apply_correct_tier, axis=1)

    # 使用量のカウント(count)で件数を取得し、総使用量を合算
    agg_df = df_target.groupby('Current_Tier', as_index=False).agg(
        件数=('使用量', 'count'),
        総使用量=('使用量', 'sum')
    )
    
    agg_df['件数'] = agg_df['件数'].astype(int)
    agg_df['総使用量'] = agg_df['総使用量'].astype(float)

    # 並び順固定（master_repがなくなったため、A, B, C...のアルファベット順を明示的に指定）
    tier_order = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'Unknown': 99}
    agg_df['order'] = agg_df['Current_Tier'].map(lambda x: tier_order.get(x, 99))
    agg_df = agg_df.sort_values('order').drop(columns=['order'])
    # --- 表示 ---
    st.markdown("---")
    total_count = agg_df['件数'].sum()
    total_vol = agg_df['総使用量'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("合計件数", f"{total_count:,.0f} 件")
    c2.metric("合計使用量", f"{total_vol:,.0f} m³")
    if total_count > 0:
        c3.metric("1件あたり平均", f"{total_vol/total_count:.1f} m³")

    if not agg_df.empty and total_count > 0:
        g1, g2 = st.columns(2)
        chic_colors = ['#88a0b9', '#aab7b8', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f']
        
        with g1:
            # 【変更】調定数 -> 件数
            fig1 = px.pie(agg_df, values='件数', names='Current_Tier', hole=0.5, 
                          color_discrete_sequence=chic_colors, title="件数シェア")
            st.plotly_chart(fig1, use_container_width=True)
        with g2:
            fig2 = px.pie(agg_df, values='総使用量', names='Current_Tier', hole=0.5, 
                          color_discrete_sequence=chic_colors, title="使用量シェア")
            st.plotly_chart(fig2, use_container_width=True)

        agg_df['構成比(件数)'] = (agg_df['件数'] / total_count * 100).map('{:.1f}%'.format)
        agg_df['構成比(使用量)'] = (agg_df['総使用量'] / (total_vol if total_vol > 0 else 1) * 100).map('{:.1f}%'.format)
        
        # テーブル表示
        st.dataframe(agg_df[['Current_Tier', '件数', '構成比(件数)', '総使用量', '構成比(使用量)']], hide_index=True, use_container_width=True)
        
        # 【指示4】シミュレーション結果(集計結果)をCSV出力できるようにする
        st.markdown("---")
        csv_data = agg_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="💾 集計結果をCSV出力",
            data=csv_data,
            file_name=f"gasio_mini_result_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

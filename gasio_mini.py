import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio mini", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 3rem; font-weight: 800; color: #2c3e50; text-align: left; }
    .sub-title { font-size: 1.2rem; color: #7f8c8d; text-align: left; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px;}
    .stMetric { background-color: #f8f9fa; border-radius: 5px; padding: 10px; border-left: 4px solid #3498db; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Gasio mini</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Final Stable Version</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義
# ---------------------------------------------------------
def normalize_columns(df):
    rename_map = {
        '基本': '基本料金', '基礎料金': '基本料金', 'Base': '基本料金',
        '単位': '単位料金', '単価': '単位料金', '従量料金': '単位料金',
        '上限': 'MAX', '下限': 'MIN', 'ID': '料金表番号', 'Code': '料金表番号',
        'Usage': '使用量', 'usage': '使用量', 'Vol': '使用量',
        '調定': '調定数', 'BillingCount': '調定数', '取付': '取付数'
    }
    df = df.rename(columns=rename_map)
    if '料金表番号' not in df.columns: df['料金表番号'] = 10
    
    # 【鉄壁】数値型の強制変換とNaN埋め
    for col in ['使用量', '調定数']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if '調定数' not in df.columns: df['調定数'] = 1
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

def get_standard_tier_label(usage, sorted_master):
    if sorted_master.empty: return "Unknown"
    u = float(usage)
    # 浮動小数点の誤差を考慮（1e-9）
    applicable = sorted_master[sorted_master['MAX'] >= (u - 1e-9)]
    row = applicable.iloc[0] if not applicable.empty else sorted_master.iloc[-1]
    min_val = row['MIN'] if 'MIN' in row else 0
    return f"{min_val:g} - {row['MAX']:g} m³"

# ---------------------------------------------------------
# 3. メイン処理
# ---------------------------------------------------------
if file_usage := st.sidebar.file_uploader("1. 使用量CSV", type=['csv']):
    if file_master := st.sidebar.file_uploader("2. 料金表マスタCSV", type=['csv']):
        df_usage = smart_load(file_usage)
        df_master = smart_load(file_master)
        
        if df_usage is not None and df_master is not None:
            usage_ids = sorted(df_usage['料金表番号'].unique())
            selected_ids = st.multiselect("分析対象の料金表番号を選択", usage_ids, default=usage_ids[:1])

            if selected_ids:
                # 構造チェック
                structures = {tid: tuple(sorted(df_master[df_master['料金表番号'] == tid]['MAX'].unique())) for tid in selected_ids}
                if len(set(structures.values())) > 1:
                    st.error("⚠️ 境界が一致しません。")
                    st.stop()

                # データ抽出
                df_target = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
                master_rep = df_master[df_master['料金表番号'] == selected_ids[0]].sort_values('MAX').reset_index(drop=True)
                
                # 判定と集計
                df_target['Current_Tier'] = df_target['使用量'].apply(lambda x: get_standard_tier_label(x, master_rep))
                
                # 【重要】agg_df作成時に数値を確実に保持
                agg_df = df_target.groupby('Current_Tier', as_index=False).agg({
                    '調定数': 'sum',
                    '使用量': 'sum'
                })
                agg_df = agg_df.rename(columns={'使用量': '総使用量'})
                
                # ソート順の付与
                labels_in_order = [get_standard_tier_label(r['MAX'] - 1e-6, master_rep) for _, r in master_rep.iterrows()]
                order_map = {label: i for i, label in enumerate(labels_in_order)}
                agg_df['order'] = agg_df['Current_Tier'].map(order_map)
                agg_df = agg_df.sort_values('order').drop(columns=['order'])

                # --- 表示 ---
                total_count = float(agg_df['調定数'].sum())
                total_vol = float(agg_df['総使用量'].sum())

                st.markdown("---")
                m1, m2, m3 = st.columns(3)
                m1.metric("合計調定数", f"{total_count:,.0f}")
                m2.metric("合計使用量", f"{total_vol:,.1f} m³")
                if total_count > 0: m3.metric("1件あたり平均", f"{total_vol/total_count:.1f} m³")

                # 【最終防衛ライン】数値かつ正のデータがある場合のみ描画
                if not agg_df.empty and total_count > 0:
                    g1, g2 = st.columns(2)
                    chic_colors = ['#88a0b9', '#82e0aa', '#f5b7b1', '#d7bde2', '#f9e79f', '#aab7b8']
                    
                    with g1:
                        st.write("**調定数シェア**")
                        # valuesに渡す列を明示的にfloat変換
                        fig1 = px.pie(agg_df, values=agg_df['調定数'].astype(float), names='Current_Tier', 
                                      hole=0.5, color_discrete_sequence=chic_colors, sort=False)
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with g2:
                        st.write("**使用量シェア**")
                        if total_vol > 0:
                            fig2 = px.pie(agg_df, values=agg_df['総使用量'].astype(float), names='Current_Tier', 
                                          hole=0.5, color_discrete_sequence=chic_colors, sort=False)
                            st.plotly_chart(fig2, use_container_width=True)

                    # 表示用テーブル（フォーマット済み）
                    display_df = agg_df.copy()
                    display_df['調定数構成比'] = (display_df['調定数'] / total_count * 100).map('{:.1f}%'.format)
                    display_df['使用量構成比'] = (display_df['総使用量'] / (total_vol if total_vol > 0 else 1) * 100).map('{:.1f}%'.format)
                    st.dataframe(display_df[['Current_Tier', '調定数', '調定数構成比', '総使用量', '使用量構成比']], 
                                 hide_index=True, use_container_width=True)
                else:
                    st.warning("表示データがありません。")
else:
    st.info("👈 サイドバーからCSVをアップロードしてください。")

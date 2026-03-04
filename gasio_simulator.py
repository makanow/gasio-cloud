import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ---------------------------------------------------------
# 1. 設定 & デザイン (UIの純粋化)
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio計算機", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.8rem; font-weight: 800; color: #2c3e50; margin-bottom: 0; }
    .sub-title { font-size: 1rem; color: #7f8c8d; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }
    .guide-box { background-color: #f0f7ff; border: 1px solid #d0e2ff; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
    .guide-title { font-weight: bold; color: #0043ce; margin-bottom: 8px; display: flex; align-items: center; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> シミュレーター</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">料金改定インパクト分析</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義 (計算ロジックの最適化)
# ---------------------------------------------------------
def calc_bill(usage, base, tiers_list):
    """新料金計算：使用量に基づき適切な単価を適用"""
    if usage <= 0: return base
    for t in tiers_list:
        if t['min'] <= usage <= t['max']:
            return base + (usage * t['price'])
    return base + (usage * tiers_list[-1]['price'])

# ---------------------------------------------------------
# 3. サイドバー: 入力ガイダンス & 設定
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 データ読み込み")
    
    # ガイダンス表示 (Data Managerの仕様を継承)
    st.markdown("""
    <div class="guide-box">
        <div class="guide-title">ℹ️ インポートガイダンス</div>
        <small>
        <b>1. 料金表マスター</b><br>
        [料金表番号, MIN, MAX, 基本料金, 単価]<br><br>
        <b>2. 請求データ</b><br>
        [料金表番号, 使用量, 調定数]<br>
        ※「取り付け数」等は不要です。
        </small>
    </div>
    """, unsafe_allow_html=True)

    file_m = st.file_uploader("1. 料金表マスター(CSV)", type="csv")
    file_u = st.file_uploader("2. 請求データ(CSV)", type="csv")
    
    st.divider()
    st.header("⚙️ 新料金案の設定")
    new_base = st.number_input("新・基本料金 (円)", value=1500, step=100)
    num_tiers = st.slider("新・単価区画数", 1, 5, 3)
    
    new_tiers_list = []
    for i in range(num_tiers):
        st.markdown(f"**区画 {i+1}**")
        c1, c2 = st.columns(2)
        l_val = c1.number_input(f"上限(m³)", value=10.0*(i+1) if i<num_tiers-1 else 999.0, key=f"l_{i}")
        p_val = c2.number_input(f"単価(円)", value=600-(i*50), key=f"p_{i}")
        new_tiers_list.append({"min": 0 if i==0 else new_tiers_list[i-1]['max']+0.1, "max": l_val, "price": p_val})

# ---------------------------------------------------------
# 4. メイン処理 (計算 & 分析)
# ---------------------------------------------------------
if file_m and file_u:
    df_master = pd.read_csv(file_m)
    df_usage = pd.read_csv(file_u)

    # 必須カラムチェックと型合わせ
    df_master['料金表番号'] = df_master['料金表番号'].astype(str)
    df_usage['料金表番号'] = df_usage['料金表番号'].astype(str)
    
    # 分析対象の選択
    all_ids = sorted(df_master['料金表番号'].unique())
    selected_ids = st.multiselect("分析対象の料金表番号", all_ids, default=all_ids[:1])
    
    if selected_ids:
        # データの絞り込みと不要カラムの排除（取り付け数等はここで無視される）
        df_target = df_usage[df_usage['料金表番号'].isin(selected_ids)].copy()
        
        # --- 現行料金計算 (調定数を乗算) ---
        def get_current(row):
            m = df_master[df_master['料金表番号'] == row['料金表番号']].sort_values('MIN')
            for _, r in m.iterrows():
                if r['MIN'] <= row['使用量'] <= r['MAX']:
                    return (r['基本料金'] + (row['使用量'] * r['単価'])) * row['調定数']
            return 0

        df_target['現行合計'] = df_target.apply(get_current, axis=1)
        # --- 新料金計算 (調定数を乗算) ---
        df_target['新合計'] = df_target.apply(lambda x: calc_bill(x['使用量'], new_base, new_tiers_list) * x['調定数'], axis=1)
        df_target['差額'] = df_target['新合計'] - df_target['現行合計']

        # --- サマリー表示 ---
        st.markdown("### 📊 収益インパクト分析")
        cur_total, new_total = df_target['現行合計'].sum(), df_target['新合計'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("現行 収益総計", f"¥{cur_total:,.0f}")
        c2.metric("新料金 収益総計", f"¥{new_total:,.0f}", f"{new_total-cur_total:+,.0f}")
        c3.metric("増減率", f"{(new_total/cur_sum-1)*100:+.2f}%" if cur_total > 0 else "0%")

        # --- 可視化 ---
        st.divider()
        fig_hist = px.histogram(df_target, x="使用量", y="調定数", nbins=50, 
                               title="使用量分布 (調定数重み付け)",
                               color_discrete_sequence=['#3498db'])
        st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader("📋 シミュレーション結果データ")
        # 表示するカラムを絞り込み（不要なデータは見せない）
        display_cols = ['料金表番号', '使用量', '調定数', '現行合計', '新合計', '差額']
        st.dataframe(df_target[display_cols].head(100), use_container_width=True)
else:
    st.info("左側のサイドバーからCSVファイルをアップロードしてください。")

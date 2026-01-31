import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ---------------------------------------------------------
# 1. デザイン & 設定 (Gasio Mini Style)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gasio mini", 
    page_icon="🔥",
    layout="centered" # スマホで見やすいよう、あえて中央寄せ
)

# カスタムCSS (Miniは少しポップに)
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .main-title {
        font-size: 2.5rem; font-weight: 800; color: #2c3e50;
        margin-bottom: 0px; letter-spacing: -1px; text-align: center;
    }
    .sub-title {
        font-size: 1.0rem; color: #95a5a6; margin-bottom: 30px;
        text-align: center; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;
    }
    div.stButton > button { width: 100%; border-radius: 20px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> mini</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Instant Usage Visualizer</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. データ読込 & 正規化
# ---------------------------------------------------------
def load_data(file):
    try:
        try: df = pd.read_csv(file, encoding='cp932')
        except: df = pd.read_csv(file, encoding='utf-8')
        
        # カラム名の正規化 (使用量さえあればいい)
        rename_map = {'使用量':'Usage', 'Usage':'Usage', 'vol':'Usage', 'Volume':'Usage'}
        df = df.rename(columns=rename_map)
        
        # 使用量カラムを探す
        target_col = None
        for col in df.columns:
            if 'Usage' in col or '使用量' in col:
                target_col = col; break
        
        if target_col:
            df = df.rename(columns={target_col: 'Usage'})
            # 数値化 & 欠損処理
            df['Usage'] = pd.to_numeric(df['Usage'], errors='coerce').fillna(0)
            return df
        else:
            return None
    except: return None

# ---------------------------------------------------------
# 3. メイン処理
# ---------------------------------------------------------
file = st.file_uploader("📂 使用量データ (CSV) をドロップ", type=['csv'])

if file:
    df = load_data(file)
    if df is not None:
        # KPI表示
        total_count = len(df)
        total_vol = df['Usage'].sum()
        avg_vol = df['Usage'].mean()
        max_vol = df['Usage'].max()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("データ件数", f"{total_count:,}", "Records")
        k2.metric("総使用量", f"{total_vol:,.0f} m³", "Total")
        k3.metric("平均使用量", f"{avg_vol:.1f} m³", "Avg")
        
        st.markdown("---")
        
        # --- 動的スライサー (Dynamic Tiering) ---
        st.subheader("🎚️ 境界線シミュレーター")
        st.caption("スライダーを動かして、区画（A/B/C）のシミュレーションができます")
        
        # スライダーで境界値を設定 (最大値に合わせてレンジを調整)
        slider_max = int(min(max_vol, 500)) # あまり大きすぎると操作しづらいので500m3キャップ
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            th_a = st.slider("A区画の上限 (m³)", 0, slider_max, 20, key="th_a")
        with col_s2:
            th_b = st.slider("B区画の上限 (m³)", th_a, slider_max, max(th_a, 50), key="th_b")
            
        # 区画判定ロジック
        def get_tier(x):
            if x <= th_a: return f"A (0-{th_a})"
            elif x <= th_b: return f"B ({th_a}-{th_b})"
            else: return f"C ({th_b}-∞)"
            
        df['Tier'] = df['Usage'].apply(get_tier)
        
        # 集計
        agg = df.groupby('Tier').agg(
            Count=('Usage', 'count'),
            Volume=('Usage', 'sum')
        ).reset_index()
        
        # 可視化エリア
        t1, t2 = st.tabs(["📊 構成比 (Pie)", "📈 分布 (Hist)"])
        
        with t1:
            c1, c2 = st.columns(2)
            # Gasio Color Palette
            colors = ['#88a0b9', '#f5b7b1', '#aab7b8']
            
            fig_count = px.pie(agg, values='Count', names='Tier', title="件数シェア", hole=0.6, color_discrete_sequence=colors)
            fig_count.update_traces(textinfo='percent+label')
            c1.plotly_chart(fig_count, use_container_width=True)
            
            fig_vol = px.pie(agg, values='Volume', names='Tier', title="使用量シェア", hole=0.6, color_discrete_sequence=colors)
            fig_vol.update_traces(textinfo='percent+label')
            c2.plotly_chart(fig_vol, use_container_width=True)
            
            st.dataframe(agg.style.format({'Volume': '{:,.1f}'}), use_container_width=True)

        with t2:
            # ヒストグラム
            fig_hist = px.histogram(df, x="Usage", nbins=100, title="使用量度数分布", color_discrete_sequence=['#3498db'])
            # 境界線を縦線で表示
            fig_hist.add_vline(x=th_a, line_dash="dash", line_color="#e74c3c", annotation_text=f"A上限: {th_a}")
            fig_hist.add_vline(x=th_b, line_dash="dash", line_color="#e74c3c", annotation_text=f"B上限: {th_b}")
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)

    else:
        st.error("CSVに使用量データ（'使用量', 'Usage' 等）が見つかりませんでした。")
else:
    st.info("👆 上のボックスにCSVをドラッグ＆ドロップしてください。")
    st.markdown("""
    ##### How to use
    1. 顧客の**使用量データ**が入ったCSVをアップロードします。
    2. 自動的に集計され、全体のボリューム感がわかります。
    3. **スライダー**を動かすと、「もしここで区画を区切ったら、A区画は何％になるか？」が瞬時にわかります。
    """)
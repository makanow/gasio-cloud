import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import datetime

# ---------------------------------------------------------
# 1. 設定 & デザイン
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio Simulator Pro", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; }
    .sub-title { font-size: 1rem; color: #7f8c8d; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
    .demo-badge { background-color: #9b59b6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> Simulator Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">高度料金シミュレーション & 個別影響分析</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 関数定義 (デモデータ生成)
# ---------------------------------------------------------
def generate_demo_data():
    """テスト用のダミーデータを生成"""
    # 料金表マスター(デモ)
    master_data = [
        {"料金表番号": "1", "料金表名": "標準プラン(デモ)", "MIN": 0.0, "MAX": 10.0, "基本料金": 1000, "単価": 600},
        {"料金表番号": "1", "料金表名": "標準プラン(デモ)", "MIN": 10.1, "MAX": 999.0, "基本料金": 1500, "単価": 550},
        {"料金表番号": "2", "料金表名": "エコプラン(デモ)", "MIN": 0.0, "MAX": 20.0, "基本料金": 1200, "単価": 580},
        {"料金表番号": "2", "料金表名": "エコプラン(デモ)", "MIN": 20.1, "MAX": 999.0, "基本料金": 2000, "単価": 500}
    ]
    df_m = pd.DataFrame(master_data)
    
    # 請求データ(デモ: 150件)
    usage_data = []
    for i in range(1, 151):
        p_id = "1" if i <= 100 else "2"
        base_u = 15.0 + np.random.rand() * 20.0
        # 5人目だけ異常に使う（アラート用）
        if i == 5: base_u = 80.0
        usage_data.append({"料金番号": f"MTR-{i:04d}", "料金表番号": p_id, "使用量": base_u, "調定数": 1})
    df_u = pd.DataFrame(usage_data)
    
    return df_m, df_u

def calc_bill(usage, base, tiers_df):
    """新料金計算ロジック"""
    if usage == 0: return base
    # Pythonでの計算を高速化するため、適切な単価を抽出
    for idx, row in tiers_df.iterrows():
        if row['MIN'] <= usage <= row['MAX']:
            return base + (usage * row['単価'])
    # 該当なし（上限超え）は最終行の単価を適用
    return base + (usage * tiers_df.iloc[-1]['単価'])

def get_current_bill(usage, p_id, df_master):
    """現行料金計算"""
    tiers = df_master[df_master['料金表番号'] == p_id].sort_values('MIN')
    if tiers.empty: return 0
    for idx, row in tiers.iterrows():
        if row['MIN'] <= usage <= row['MAX']:
            return row['基本料金'] + (usage * row['単価'])
    return tiers.iloc[-1]['基本料金'] + (usage * tiers.iloc[-1]['単価'])

# ---------------------------------------------------------
# 3. サイドバー・データ読み込み
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 データ入力")
    use_demo = st.checkbox("✨ デモモードを使用", value=False)
    
    if not use_demo:
        file_m = st.file_uploader("1. 料金表マスター(CSV)", type="csv")
        file_u = st.file_uploader("2. 請求データ(CSV)", type="csv")
    
    st.divider()
    st.header("⚙️ 新料金設定")
    new_base = st.number_input("新・基本料金 (円)", value=2000, step=100)
    
    # 動的な区画設定
    num_tiers = st.slider("新料金の区画数", 1, 5, 3)
    new_tiers_list = []
    for i in range(num_tiers):
        c1, c2 = st.columns(2)
        with c1:
            limit = st.number_input(f"区画{i+1}上限(m3)", value=(i+1)*10.0 if i < num_tiers-1 else 999.0, key=f"lim_{i}")
        with c2:
            price = st.number_input(f"区画{i+1}単価(円)", value=600-(i*50), key=f"prc_{i}")
        new_tiers_list.append({"MIN": 0 if i==0 else new_tiers_list[i-1]["MAX"]+0.1, "MAX": limit, "単価": price})
    df_new_tiers = pd.DataFrame(new_tiers_list)

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
df_master_all, df_usage_all = None, None

if use_demo:
    df_master_all, df_usage_all = generate_demo_data()
    st.info("💡 現在デモモードで動作中です。")
elif file_m and file_u:
    df_master_all = pd.read_csv(file_m)
    df_usage_all = pd.read_csv(file_u)

if df_master_all is not None and df_usage_all is not None:
    # --- 計算実行 ---
    # 現行料金の計算
    df_usage_all['現行料金'] = df_usage_all.apply(lambda x: get_current_bill(x['使用量'], str(x['料金表番号']), df_master_all), axis=1)
    # 新料金の計算
    df_usage_all['新料金'] = df_usage_all.apply(lambda x: calc_bill(x['使用量'], new_base, df_new_tiers), axis=1)
    
    df_usage_all['差額'] = df_usage_all['新料金'] - df_usage_all['現行料金']
    df_usage_all['上昇率'] = (df_usage_all['差額'] / df_usage_all['現行料金']).replace([np.inf, -np.inf], 0).fillna(0)

    # --- サマリー表示 ---
    cur_total = df_usage_all['現行料金'].sum()
    new_total = df_usage_all['新料金'].sum()
    diff_total = new_total - cur_total
    diff_pct = (diff_total / cur_total * 100) if cur_total > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("現行 総収益", f"¥{cur_total:,.0f}")
    m2.metric("新料金 総収益", f"¥{new_total:,.0f}", f"{diff_total:,.0f}")
    m3.metric("収益インパクト", f"{diff_pct:+.2f}%", delta_color="normal")

    # --- アラート分析 ---
    st.divider()
    st.subheader("⚠️ 個別影響（値上げアラート）分析")
    
    threshold = st.slider("検知しきい値（%以上の値上げ）", 0, 100, 20)
    anomalies = df_usage_all[df_usage_all['上昇率'] >= (threshold / 100)].sort_values('上昇率', ascending=False)
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.metric("アラート対象件数", f"{len(anomalies)} 件", f"全 {len(df_usage_all)} 件中")
        if not anomalies.empty:
            csv = anomalies.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 アラート顧客リスト(CSV)を保存", data=csv, file_name="gasio_alerts.csv", mime="text/csv")
    
    with col_b:
        if not anomalies.empty:
            st.dataframe(anomalies[['料金番号', '使用量', '現行料金', '新料金', '上昇率']].style.format({
                '使用量': '{:.1f}', '現行料金': '¥{:,.0f}', '新料金': '¥{:,.0f}', '上昇率': '{:.1%}'
            }), hide_index=True)
        else:
            st.success("✅ 設定したしきい値を超える大幅な値上げ対象はいません。")

    # --- グラフ表示 ---
    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        # 使用量 vs 上昇率の散布図
        fig_scatter = px.scatter(df_usage_all, x="使用量", y="上昇率", color="料金表番号", 
                                 title="使用量ごとの上昇率分布", hover_data=["料金番号"])
        fig_scatter.add_hline(y=threshold/100, line_dash="dash", line_color="red")
        st.plotly_chart(fig_scatter, use_container_width=True)
    with g2:
        # 収益比較
        fig_rev = go.Figure(data=[
            go.Bar(name='現行', x=['総収益'], y=[cur_total], marker_color='#95a5a6'),
            go.Bar(name='新料金', x=['総収益'], y=[new_total], marker_color='#e67e22')
        ])
        fig_rev.update_layout(title="総収益比較", barmode='group')
        st.plotly_chart(fig_rev, use_container_width=True)

else:
    st.warning("👈 サイドバーからファイルをアップロードするか、『デモモード』をオンにしてください。")
    #

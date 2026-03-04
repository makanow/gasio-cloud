import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ---------------------------------------------------------
# デザイン設定（既存のものを維持）
# ---------------------------------------------------------
st.set_page_config(page_title="Gasio Simulator Pro", page_icon="🔥", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 800; color: #2c3e50; margin-bottom: 0px; }
    .sub-title { font-size: 1rem; color: #7f8c8d; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><span style="color:#2c3e50">Gas</span><span style="color:#e74c3c">i</span><span style="color:#3498db">o</span> Simulator Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">シミュレーション & 安全性チェック</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 計算ロジック（既存ロジックを尊重しつつ拡張）
# ---------------------------------------------------------
def calc_bill_safe(usage, base, tiers_df):
    if usage == 0: return base
    # 該当する区画を検索
    match = tiers_df[(tiers_df['MIN'] <= usage) & (usage <= tiers_df['MAX'])]
    if not match.empty:
        return base + (usage * match.iloc[0]['単価'])
    return base + (usage * tiers_df.iloc[-1]['単価'])

def get_current_bill_safe(usage, p_id, df_master):
    tiers = df_master[df_master['料金表番号'].astype(str) == str(p_id)].sort_values('MIN')
    if tiers.empty: return 0
    match = tiers[(tiers['MIN'] <= usage) & (usage <= tiers['MAX'])]
    if not match.empty:
        return match.iloc[0]['基本料金'] + (usage * match.iloc[0]['単価'])
    return tiers.iloc[-1]['基本料金'] + (usage * tiers.iloc[-1]['単価'])

# ---------------------------------------------------------
# サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 データ読み込み")
    # デモモードは選択式にし、既存のアップローダーを邪魔しない
    use_demo = st.toggle("✨ デモデータで試す", value=False)
    
    file_m = st.file_uploader("1. 料金表マスター(CSV)", type="csv")
    file_u = st.file_uploader("2. 請求データ(CSV)", type="csv")
    
    st.divider()
    st.header("⚙️ 新料金パラメータ")
    new_base = st.number_input("新・基本料金", value=2000)
    num_tiers = st.slider("新料金の区画数", 1, 5, 3)
    
    new_tiers = []
    for i in range(num_tiers):
        c1, c2 = st.columns(2)
        limit = c1.number_input(f"区画{i+1}上限", value=(i+1)*10.0 if i<num_tiers-1 else 999.0, key=f"l_{i}")
        price = c2.number_input(f"区画{i+1}単価", value=600-(i*50), key=f"p_{i}")
        new_tiers.append({"MIN": 0 if i==0 else new_tiers[i-1]["MAX"]+0.1, "MAX": limit, "単価": price})
    df_new_tiers = pd.DataFrame(new_tiers)

# ---------------------------------------------------------
# メインロジック
# ---------------------------------------------------------
df_m, df_u = None, None

# データソースの確定
if use_demo:
    # 既存のデモ生成ロジックを安全に呼び出し
    master_data = [{"料金表番号": "1", "MIN": 0.0, "MAX": 999.0, "基本料金": 1500, "単価": 550}]
    usage_data = [{"料金番号": f"ID-{i}", "料金表番号": "1", "使用量": np.random.randint(5, 50), "調定数": 1} for i in range(100)]
    df_m, df_u = pd.DataFrame(master_data), pd.DataFrame(usage_data)
elif file_m and file_u:
    df_m, df_u = pd.read_csv(file_m), pd.read_csv(file_u)

if df_m is not None and df_u is not None:
    # 既存のカラム名チェック
    col_id = "料金番号" if "料金番号" in df_u.columns else df_u.columns[0]
    
    # 計算処理
    df_u['現行料金'] = df_u.apply(lambda x: get_current_bill_safe(x['使用量'], x['料金表番号'], df_m), axis=1)
    df_u['新料金'] = df_u.apply(lambda x: calc_bill_safe(x['使用量'], new_base, df_new_tiers), axis=1)
    df_u['上昇率'] = (df_u['新料金'] / df_u['現行料金'] - 1).fillna(0)

    # サマリー
    st.subheader("📊 シミュレーション結果")
    m1, m2, m3 = st.columns(3)
    m1.metric("現行総収益", f"¥{df_u['現行料金'].sum():,.0f}")
    m2.metric("新料金総収益", f"¥{df_u['新料金'].sum():,.0f}", f"{df_u['新料金'].sum() - df_u['現行料金'].sum():+,.0f}")
    
    # アラート機能（ここが今回の改善点）
    st.divider()
    st.subheader("⚠️ 個別影響アラート")
    threshold = st.slider("アラートしきい値（%以上の値上げ）", 0, 100, 20) / 100
    anomalies = df_u[df_u['上昇率'] >= threshold].copy()
    
    if not anomalies.empty:
        st.error(f"対象顧客が {len(anomalies)} 件見つかりました。")
        st.dataframe(anomalies[[col_id, '使用量', '現行料金', '新料金', '上昇率']].style.format({'上昇率': '{:.1%}'}))
    else:
        st.success("大幅な値上げ対象の顧客はいません。")

    # グラフ（エラー回避策：hover_dataに実在するカラムのみ指定）
    fig = px.scatter(df_u, x="使用量", y="上昇率", title="使用量 vs 影響度",
                     hover_data=[col_id] if col_id in df_u.columns else None)
    fig.add_hline(y=threshold, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("データを読み込んでください。")

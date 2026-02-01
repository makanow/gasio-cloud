import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# 1. ページ設定とスタイル
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master PoC", layout="wide")
st.markdown("""
    <style>
    .logic-box { background-color: #f0f2f6; border-radius: 10px; padding: 20px; border: 1px solid #dcdfe3; }
    .metric-label { font-size: 1.2rem; font-weight: bold; color: #555; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ G-Calc Pilot: 労務費ハイブリッド算定")

EXCEL_FILE = "G-Calc_master.xlsx"

# ---------------------------------------------------------
# 2. 賢いデータ抽出関数
# ---------------------------------------------------------
@st.cache_data
def get_val(sheet_name, keyword, offset_row=0, offset_col=1):
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name, header=None)
        for i, row in df.iterrows():
            for j, val in enumerate(row):
                if str(val).strip() == keyword:
                    return df.iloc[i + offset_row, j + offset_col]
        return None
    except:
        return None

# Excelから基本データを吸い出す
with st.spinner('要塞からデータを抽出中...'):
    base_cust_count = get_val("ナビ", "許可地点数*") or 245.0
    std_coeff = get_val("1_b", "１供給地点当たり所要人数(d1)") or 0.0031
    avg_wage = get_val("1_b", "１人当たり年間平均労務費(d4)") or 7104000.0

# ---------------------------------------------------------
# 3. メインUI：コックピット
# ---------------------------------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.header("🎮 パラメータ入力")
    
    # 地点数の変更シミュレーション
    customer_count = st.number_input("供給地点数 (a2)", value=float(base_cust_count), step=1.0)
    
    st.divider()
    
    # 【ハイブリッド選択】
    calc_mode = st.radio(
        "労務費の決定方法を選んでくれ",
        ["理論値（標準係数による計算）", "実績値（直接入力）"],
        help="役所への説明根拠に応じて切り替えます"
    )

    if calc_mode == "実績値（直接入力）":
        labor_cost_input = st.number_input("実績労務費（円）", value=5395488, step=1000)
    else:
        st.info("💡 現在はExcelの算定式に基づいて自動計算されています")

with col2:
    st.header("📊 算定結果")
    
    # ロジックの実行
    if calc_mode == "理論値（標準係数による計算）":
        # 理論計算：地点数 × 係数 × 平均賃金
        personnel = std_coeff * customer_count
        final_labor_cost = personnel * avg_wage
        status_msg = "✅ 標準係数に基づき算定中"
    else:
        final_labor_cost = labor_cost_input
        status_msg = "⚠️ 実績値による上書き中"

    st.markdown(f"**{status_msg}**")
    st.metric("採用される労務費", f"{final_labor_cost:,.0f} 円")
    
    # 差分の表示（Excel初期値との比較）
    diff = final_labor_cost - 5395488
    st.metric("初期設定からの増減", f"{diff:,.0f} 円", delta=diff)

# ---------------------------------------------------------
# 4. ロジック公開モード（ここがナガセのこだわり！）
# ---------------------------------------------------------
st.divider()
show_logic = st.checkbox("📖 ロジック公開モードを起動する（審査・教育用）")

if show_logic:
    st.subheader("🔍 算定根拠の解体新書")
    
    if calc_mode == "理論値（標準係数による計算）":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="logic-box">
                <b>【計算プロセス】</b><br>
                1. 所要人員の算出<br>
                &nbsp;&nbsp; {customer_count}地点 × {std_coeff} = {std_coeff * customer_count:.4f}人<br>
                2. 労務費の算出<br>
                &nbsp;&nbsp; {std_coeff * customer_count:.4f}人 × {avg_wage:,.0f}円 = <b>{final_labor_cost:,.0f}円</b>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.write("📖 **解説**")
            st.write("この計算は、ガス事業許可申請における「標準的な効率経営」を前提としたものです。地点数が増加すると、標準係数に従って必要な人員と費用が比例して算出されます。")
    else:
        st.markdown(f"""
        <div class="logic-box">
            <b>【実績採用の根拠】</b><br>
            理論値（{(std_coeff * customer_count * avg_wage):,.0f}円）ではなく、直近の決算実績値を優先採用しました。<br>
            理由：現行の地点数における実働人員が理論値を上回っているため。
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 【予告】履歴保存ボタン（次回実装）
# ---------------------------------------------------------
if st.button("💾 この算定結果を「埼玉エリア・2024改定」として保存する（準備中）"):
    st.snow()
    st.write("※月曜日にデータベース連携を実装するぞ！お楽しみに！")

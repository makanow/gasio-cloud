import streamlit as st
import pandas as pd

st.set_page_config(page_title="G-Calc PoC", layout="wide")
st.title("🛡️ G-Calc パイロットテスト：自動サーチ・エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

@st.cache_data
def load_gcalc_val(keyword):
    try:
        # Excelの「ナビ」シートを読み込み
        df = pd.read_excel(EXCEL_FILE, sheet_name='ナビ', header=None)
        
        # 全セルをスキャンしてキーワードを探す
        for i, row in df.iterrows():
            for j, val in enumerate(row):
                if str(val).strip() == keyword:
                    # キーワードの1つ右、または2つ右のセルに数値があると仮定
                    # 今回の「ナビ」シートの構造に合わせて「1つ右(j+1)」を取得
                    found_val = df.iloc[i, j+1]
                    return float(found_val)
        return None
    except Exception as e:
        st.error(f"サーチ失敗：{e}")
        return None

# ---------------------------------------------------------
# 実行
# ---------------------------------------------------------
st.header("🎮 算定パラメータ・スキャン")

# 「許可地点数*」をキーワードに検索
scanned_count = load_gcalc_val("許可地点数*")

if scanned_count is not None:
    st.success(f"✅ Excelから値を救出したぞ！ 座標自動検知完了。")
    customer_count = st.number_input("供給地点数 (自動取得値)", value=scanned_count)
else:
    st.warning("⚠️ キーワードが見つからない。手入力してくれ。")
    customer_count = st.number_input("供給地点数 (手入力)", value=245.0)

# 簡易計算テスト
std_coeff = 0.0031
avg_wage = 7104000
theory_cost = customer_count * std_coeff * avg_wage

st.divider()
st.metric("算定された労務費 (理論値)", f"{theory_cost:,.0f} 円")

if st.checkbox("📖 内部構造を表示（デバッグ用）"):
    st.write("現在、PythonはこのようにExcelを認識しているぞ：")
    df_debug = pd.read_excel(EXCEL_FILE, sheet_name='ナビ', header=None)
    st.dataframe(df_debug.head(15))

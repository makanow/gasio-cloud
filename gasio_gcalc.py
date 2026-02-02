import streamlit as st
import pandas as pd
import math

# 1. ページ構成
st.set_page_config(page_title="Gas Lab Engine v3.2", layout="wide")

# 数値変換ユーティリティ（文字列や空欄を安全に数値化）
def clean_num(val):
    try:
        if pd.isna(val): return 0.0
        # 文字列として扱い、カンマや単位を除去してから変換
        s = str(val).replace(',', '').replace('㎡', '').replace('円', '').strip()
        return float(s)
    except:
        return 0.0

# 2. 初期化
if 'db' not in st.session_state:
    st.session_state.db = {
        "land_id": "11", "use_reduction": True, "active_return_rate": 0.03,
        "res_land_area": 0.0, "res_land_invest": 0.0, "res_land_eval": 0.0,
        "invest_1": 0.0, "invest_2": 0.0, "res_tax": 0.0, "res_return": 0.0, "res_dep": 0.0
    }
db = st.session_state.db

# 3. 計算ロジック
def run_logic(df_land=None, df_assets=None):
    # --- A. 土地：クレンジング後に計算 ---
    if df_land is not None:
        try:
            # A1, B1, C1 セルの値を安全に取得
            act_area = clean_num(df_land.iloc[0, 0])
            act_price = clean_num(df_land.iloc[0, 1])
            act_eval = clean_num(df_land.iloc[0, 2])
            
            if act_area > 0:
                req_area = 295.0
                db["res_land_area"] = min(act_area, req_area)
                # ROUND(単価, 0)
                u_price = round(act_price / act_area, 0)
                db["res_land_invest"] = u_price * db["res_land_area"]
                u_eval = round(act_eval / act_area, 0)
                db["res_land_eval"] = u_eval * db["res_land_area"]
        except Exception as e:
            st.error(f"土地データの処理に失敗しました: {e}")

    # --- B. 償却資産：行列指定で集計 ---
    if df_assets is not None:
        try:
            # 列を数値化してから集計（I列:8, K列:10）
            df_assets.iloc[:, 10] = df_assets.iloc[:, 10].apply(clean_num)
            
            db["invest_2"] = df_assets[df_assets.iloc[:, 8] == 1].iloc[:, 10].sum()
            db["invest_1"] = df_assets[df_assets.iloc[:, 8] != 1].iloc[:, 10].sum() + db.get("res_land_invest", 0)
        except Exception as e:
            st.error(f"資産データの処理に失敗しました: {e}")

    # --- C. 財務計算（端数処理徹底） ---
    tax_base = db["invest_1"] + (db["invest_2"] * 0.5)
    db["res_tax"] = math.floor(tax_base * 0.014) + math.floor(db["res_land_eval"] * 0.014)
    db["res_return"] = math.floor((db["invest_1"] + db["invest_2"]) * db["active_return_rate"])
    db["res_dep"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)

# 4. UIセクション
st.title("🧪 Gas Lab Engine : 堅牢データ統合版")

with st.sidebar:
    st.header("📂 データ・アップロード")
    file_land = st.file_uploader("土地情報シート (CSV)", type="csv")
    file_assets = st.file_uploader("償却資産シート (CSV)", type="csv")
    
    if st.button("🚀 計算実行"):
        # Shift-JIS(Excel日本語)とUTF-8の両方に対応を試みる
        try:
            df_l = pd.read_csv(file_land, encoding='cp932') if file_land else None
            df_a = pd.read_csv(file_assets, encoding='cp932') if file_assets else None
        except:
            df_l = pd.read_csv(file_land) if file_land else None
            df_a = pd.read_csv(file_assets) if file_assets else None
            
        run_logic(df_l, df_a)

# --- 以下、Dashboard表示部分は v3.1 と同様 ---
# (省略するが、実際のコードには含める)
st.header("📊 算定 Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("推定総括原価", f"¥{db['res_dep']+db['res_tax']+db['res_return']:,.0f}")
c2.metric("租税公課", f"¥{db['res_tax']:,.0f}")
c3.metric("事業報酬", f"¥{db['res_return']:,.0f}")

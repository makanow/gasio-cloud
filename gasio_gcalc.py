import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Gas Lab Engine : High Reliability", layout="wide")

# 初期化
if 'db' not in st.session_state:
    st.session_state.db = {"res_land_invest": 0, "invest_1": 0, "invest_2": 0}
db = st.session_state.db

def get_possible_raw_urls(base_url):
    """main または master ブランチの両方の可能性を考慮したURLリストを生成"""
    # ユーザーが入力したURLから余計な部分（/blob/等）を削ぎ落とす
    base = base_url.rstrip('/').replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    # G-Calc_master.xlsx を含むURLを複数パターン生成
    return [
        f"{base}/main/G-Calc_master.xlsx",
        f"{base}/master/G-Calc_master.xlsx",
        f"{base}/G-Calc_master.xlsx" # すでにブランチ名が含まれている場合
    ]

st.title("🧪 Gas Lab Engine : GitHub Direct Connector")

with st.sidebar:
    st.header("📂 接続設定")
    repo_input = st.text_input("GitHubリポジトリのURLを貼り付けてください")
    
    if st.button("🔄 同期開始"):
        if repo_input:
            urls = get_possible_raw_urls(repo_input)
            success = False
            
            for url in urls:
                try:
                    sheets = pd.read_excel(url, sheet_name=None)
                    # --- ロジック実行 ---
                    # 土地シートが存在する場合の処理
                    land_sheet_name = "土地" if "土地" in sheets else "土地情報"
                    if land_sheet_name in sheets:
                        df_l = sheets[land_sheet_name]
                        act_area = df_l.iloc[0, 0]
                        act_price = df_l.iloc[0, 1]
                        db["res_land_area"] = min(act_area, 295.0)
                        db["res_land_invest"] = round(act_price / act_area, 0) * db["res_land_area"]
                    
                    success = True
                    st.success(f"✅ 同期成功 (URL: {url})")
                    break # 成功したらループを抜ける
                except Exception:
                    continue # 404なら次のURLを試す
            
            if not success:
                st.error("404: ファイルが見つかりません。リポジトリ内に 'G-Calc_master.xlsx' が存在するか確認してください。")
        else:
            st.warning("URLを入力してください。")

# --- Dashboard表示 ---
st.header("📊 算定 Dashboard")
st.metric("認容土地投資額", f"¥{db.get('res_land_invest', 0):,.0f}")

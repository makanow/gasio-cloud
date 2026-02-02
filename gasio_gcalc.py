import streamlit as st
import pandas as pd
import math
import re

# 1. ページ設定
st.set_page_config(page_title="Gas Lab Engine : Auto Connector", layout="wide")

# 2. 初期化
if 'db' not in st.session_state:
    st.session_state.db = {"res_land_invest": 0, "invest_1": 0, "invest_2": 0}
db = st.session_state.db

# 3. GitHubのURLから「Rawデータ用URL」を組み立てる関数
def get_raw_url(github_url):
    # 例: https://github.com/nagase/gasio-cloud/blob/main/G-Calc_master.xlsx
    # を https://raw.githubusercontent.com/nagase/gasio-cloud/main/G-Calc_master.xlsx に変換
    raw_url = github_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    return raw_url

# 4. メイン UI
st.title("🧪 Gas Lab Engine : GitHub Direct Sync")

with st.sidebar:
    st.header("📂 接続設定")
    # ここにGitHubのURLを貼り付けてもらう
    repo_url = st.text_input(
        "GitHubのリポジトリURLを入力してください",
        placeholder="https://github.com/ユーザー名/リポジトリ名"
    )
    
    if st.button("🔄 Excelと同期開始"):
        if repo_url:
            # ファイル名 G-Calc_master.xlsx を付与してRaw URLを生成
            target_url = get_raw_url(f"{repo_url.rstrip('/')}/main/G-Calc_master.xlsx")
            
            try:
                # Excelを直接読み込み
                sheets = pd.read_excel(target_url, sheet_name=None)
                
                # --- ここでナガセのExcel構造を解析 ---
                # 仮定：シート名が「土地」「資産」などの場合
                if "土地" in sheets:
                    df_l = sheets["土地"]
                    # ナガセ指定：ROUND(取得価格/取得面積,0) * MIN(面積, 295)
                    act_area = df_l.iloc[0, 0] # A1
                    act_price = df_l.iloc[0, 1] # B1
                    db["res_land_area"] = min(act_area, 295.0)
                    db["res_land_invest"] = round(act_price / act_area, 0) * db["res_land_area"]
                
                st.success("✅ 同期に成功しました。Dashboardを確認してください。")
            except Exception as e:
                st.error(f"接続失敗。URLかファイル名を確認してください: {e}")
        else:
            st.warning("URLを入力してください。")

# --- Dashboard表示 ---
st.header("📊 算定 Dashboard")
c1, c2 = st.columns(2)
c1.metric("認容土地投資額", f"¥{db.get('res_land_invest', 0):,.0f}")

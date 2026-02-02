import streamlit as st
import math

# =================================================================
# 1. 財務計算エンジン（租税公課・事業報酬）
# =================================================================
def run_financial_engine():
    db = st.session_state.db
    
    # --- A. 減価償却費 (個別計算・端数保持) ---
    total_depreciation = 0.0
    for asset in db["assets_list"]:
        # 投資単位ごとに計算し、あえてここでは丸めない
        val = asset["actual"] if db["asset_mode"] == "実績" else asset["std"]
        dep = val * 0.03 # 償却率0.03 (標準係数A!E5:R5)
        total_depreciation += dep
    db["res_depreciation_total"] = total_depreciation # 最後に表示時に処理

    # --- B. 租税公課 (固定資産税 1.4%) ---
    # 償却資産分：(投資額① + 投資額② * 0.5) * 0.014
    # 土地分：土地評価額 * 0.014
    # Excelの動きに合わせ、課税標準額を算出して計算
    tax_base_assets = db["invest_1"] + (db["invest_2"] * 0.5)
    tax_assets = math.floor(tax_base_assets * 0.014) # 円単位切り捨て想定
    
    tax_land = math.floor(db["res_land_eval"] * 0.014)
    db["res_tax_total"] = tax_assets + tax_land

    # --- C. 事業報酬 (Rate of Return) ---
    # 報酬率の設定（標準係数B K8 or 手入力）
    if not db["override_return_rate"]:
        db["active_return_rate"] = 0.03 # 標準係数B K8 (3%)
    
    # 本則：(資産ベース + 運転資金) * 報酬率
    # 資産ベースは「期首・期末平均」だが、現在は簡易的に「現行投資額」を使用
    asset_base = db["invest_1"] + db["invest_2"] + db["res_land_invest"]
    db["res_return_on_assets"] = math.floor(asset_base * db["active_return_rate"])

# =================================================================
# 2. UIセクション：ナビゲーションと検算
# =================================================================
with st.sidebar:
    st.divider()
    st.header("⚙️ 財務・報酬設定")
    db["override_return_rate"] = st.checkbox("事業報酬率を手入力する", value=False)
    if db["override_return_rate"]:
        db["active_return_rate"] = st.number_input("事業報酬率", value=0.03, step=0.001, format="%.3f")
    else:
        st.info(f"標準報酬率: 3.000% (標準係数B K8引用)")

# Dashboardに財務結果を追加
with st.expander("🔍 財務計算プロセスの検証"):
    st.write(f"1. 減価償却費合計: ¥{db.get('res_depreciation_total', 0):,.0f}")
    st.write(f"2. 租税公課（固定資産税分）: ¥{db.get('res_tax_total', 0):,.0f}")
    st.write(f"   (内訳) 償却資産: ¥{tax_assets if 'tax_assets' in locals() else 0:,.0f} / 土地: ¥{tax_land if 'tax_land' in locals() else 0:,.0f}")
    st.write(f"3. 事業報酬: ¥{db.get('res_return_on_assets', 0):,.0f}")

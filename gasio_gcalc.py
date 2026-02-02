import streamlit as st
import pandas as pd
import openpyxl
import re

st.set_page_config(page_title="Gas Lab Engine : THE CLONE v16.1", layout="wide")

# --- 1. 万能座標・数式解析エンジン (エラー耐性強化) ---
class GasLogicEngine:
    def __init__(self, uploaded_file):
        # 演算用(値)と解析用(数式)
        self.wb_val = openpyxl.load_workbook(uploaded_file, data_only=True, read_only=True)
        self.wb_form = openpyxl.load_workbook(uploaded_file, data_only=False, read_only=True)
    
    def get_val(self, sheet, addr):
        try:
            val = self.wb_val[sheet][addr].value
            # 数値でない(Noneや文字列)場合は0.0に変換せず、後の判定のためにそのまま返す
            return val
        except: return None

    def get_formula(self, sheet, addr):
        try:
            return self.wb_form[sheet][addr].value
        except: return "N/A"

def clean_num(val):
    """Noneや文字列を安全に数値(float)に変換する"""
    if val is None or isinstance(val, str): return 0.0
    return float(val)

# --- 2. 算定ロジックの実行 ---
def run_perfect_sync(engine):
    data = {}
    
    # 【出口】別表4,5 I56
    data["final_total"] = clean_num(engine.get_val("別表4,5", "I56"))
    data["final_formula"] = engine.get_formula("別表4,5", "I56")
    
    # 【分母】販売量 O8
    data["vol_yakkan"] = clean_num(engine.get_val("販売量", "O8"))
    
    # 【内訳】
    keys = {"営業費小計": "I40", "減価償却費": "I45", "租税公課": "I48", "事業報酬": "I52"}
    data["audit"] = []
    for label, addr in keys.items():
        v = engine.get_val("別表4,5", addr)
        f = engine.get_formula("別表4,5", addr)
        data["audit"].append({
            "項目": label,
            "座標": f"別表4,5!{addr}",
            "金額": v if isinstance(v, (int, float)) else 0.0,
            "Excel数式": f
        })
    return data

# --- 3. UI構築 ---
st.title("🛡️ Gas Lab Engine : 完全再現モデル v16.1")

uploaded_file = st.file_uploader("算定Excelをアップロード", type=["xlsx"])

if uploaded_file:
    with st.spinner("Excel解析中..."):
        engine = GasLogicEngine(uploaded_file)
        data = run_perfect_sync(engine)
    
    # メイン Dashboard
    c1, c2, c3 = st.columns(3)
    c1.metric("総括原価 (I56)", f"¥{data['final_total']:,.0f}")
    c2.metric("約款販売量 (O8)", f"{data['vol_yakkan']:,.1f} m3")
    
    unit_price = data['final_total'] / data['vol_yakkan'] if data['vol_yakkan'] > 0 else 0
    c3.metric("確定供給単価", f"{unit_price:,.2f} 円/m3")

    # 監査ログ (ここでのTypeErrorを回避)
    st.subheader("🕵️ ロジック・オーディター")
    df_audit = pd.DataFrame(data["audit"])
    # 金額列のフォーマットを安全に適用
    df_audit["金額"] = df_audit["金額"].apply(lambda x: f"¥{x:,.0f}")
    st.table(df_audit)

import streamlit as st
import pandas as pd
import openpyxl
import re

st.set_page_config(page_title="Gas Lab Engine : THE CLONE", layout="wide")

# --- 1. 万能座標・数式解析エンジン ---
class GasLogicEngine:
    def __init__(self, uploaded_file):
        # 演算用(値)と解析用(数式)の二刀流
        self.wb_val = openpyxl.load_workbook(uploaded_file, data_only=True, read_only=True)
        self.wb_form = openpyxl.load_workbook(uploaded_file, data_only=False, read_only=True)
    
    def get_val(self, sheet, addr):
        return self.wb_val[sheet][addr].value

    def get_formula(self, sheet, addr):
        return self.wb_form[sheet][addr].value

# --- 2. 算定ロジックの「完全同期」 ---
def run_perfect_sync(engine):
    results = {}
    
    # 【出口】別表4,5 I56 (総括原価)
    results["final_total"] = engine.get_val("別表4,5", "I56")
    results["final_formula"] = engine.get_formula("別表4,5", "I56")
    
    # 【分母】販売量 O8 (約款分)
    results["vol_yakkan"] = engine.get_val("販売量", "O8")
    results["vol_yakkan_formula"] = engine.get_formula("販売量", "O8")
    
    # 【中身】主要経費の滝 (ホワイトボックス化)
    keys = {
        "営業費小計": "I40", "減価償却費": "I45", 
        "租税公課": "I48", "事業報酬": "I52"
    }
    for label, addr in keys.items():
        results[label] = {
            "val": engine.get_val("別表4,5", addr),
            "formula": engine.get_formula("別表4,5", addr)
        }
    
    return results

# --- 3. UI構築 ---
st.title("🛡️ Gas Lab Engine : 法廷品質・完全再現モデル")

uploaded_file = st.file_uploader("算定Excelをアップロード", type=["xlsx"])

if uploaded_file:
    engine = GasLogicEngine(uploaded_file)
    data = run_perfect_sync(engine)
    
    # 算定 Dashboard
    st.header("📊 算定結果")
    c1, c2, c3 = st.columns(3)
    c1.metric("総括原価 (I56)", f"¥{data['final_total']:,.0f}")
    c2.metric("約款販売量 (O8)", f"{data['vol_yakkan']:,.1f} m3")
    unit_price = data['final_total'] / data['vol_yakkan'] if data['vol_yakkan'] > 0 else 0
    c3.metric("確定供給単価", f"{unit_price:,.2f} 円/m3")

    # ブラックボックスの解体（完全再現の証明）
    st.subheader("🕵️ ロジック・オーディター（監査ログ）")
    audit_log = []
    for label in ["営業費小計", "減価償却費", "租税公課", "事業報酬"]:
        audit_log.append({
            "項目": label,
            "金額": f"¥{data[label]['val']:,.0f}",
            "Excel数式": data[label]['formula']
        })
    st.table(pd.DataFrame(audit_log))

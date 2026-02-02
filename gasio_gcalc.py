import streamlit as st
import pandas as pd
import openpyxl
import re

st.set_page_config(page_title="Gas Lab Engine : THE CLONE v17.0", layout="wide")

class GasLogicEngine:
    def __init__(self, uploaded_file):
        # 名前付き範囲の定義を読み込む
        self.wb_form = openpyxl.load_workbook(uploaded_file, data_only=False)
        self.wb_val = openpyxl.load_workbook(uploaded_file, data_only=True)
        # 名前付き範囲を辞書化
        self.defined_names = {}
        for dn in self.wb_form.defined_names.definedName:
            try:
                # 名前が指し示す範囲を抽出
                self.defined_names[dn.name] = dn.attr_text
            except: pass

    def resolve_name(self, name):
        """名前付き範囲を実際の座標に変換する"""
        return self.defined_names.get(name, name)

    def get_val_by_name(self, name):
        """名前から直接値を取得する"""
        ref = self.resolve_name(name)
        # 'シート名'!$A$1 形式を分割
        if '!' in ref:
            s_name, addr = ref.replace('$', '').split('!')
            try: return self.wb_val[s_name][addr].value
            except: return None
        return None

    def get_val(self, sheet, addr):
        try: return self.wb_val[sheet][addr].value
        except: return 0.0

    def get_formula(self, sheet, addr):
        try: return self.wb_form[sheet][addr].value
        except: return "N/A"

# --- UI構築 ---
st.title("🛡️ Gas Lab Engine : 名前付き範囲・完全解読 v17.0")

uploaded_file = st.file_uploader("算定Excelをアップロード", type=["xlsx"])

if uploaded_file:
    engine = GasLogicEngine(uploaded_file)
    
    # 1. 最終数値の取得
    final_cost = engine.get_val("別表4,5", "I56")
    vol_yakkan = engine.get_val("販売量", "O8")
    
    # 2. ダッシュボード表示
    c1, c2, c3 = st.columns(3)
    c1.metric("総括原価 (I56)", f"¥{final_cost:,.0f}")
    c2.metric("約款販売量 (O8)", f"{vol_yakkan:,.1f} m3")
    c3.metric("確定供給単価", f"{(final_cost/vol_yakkan if vol_yakkan else 0):,.2f} 円/m3")

    # 3. 名前付き範囲の「暴露」
    with st.expander("🕵️ 名前付き範囲（定義済みロジック）の全リスト"):
        name_list = []
        for name, ref in engine.defined_names.items():
            val = engine.get_val_by_name(name)
            name_list.append({"名前": name, "参照先": ref, "現在の値": val})
        st.table(pd.DataFrame(name_list))

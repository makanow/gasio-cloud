import streamlit as st
import pandas as pd
import openpyxl

st.set_page_config(page_title="Gas Lab Engine : THE CLONE v17.2", layout="wide")

class GasLogicEngine:
    def __init__(self, uploaded_file):
        # メモリを食わないよう読み込みを最適化
        self.wb_val = openpyxl.load_workbook(uploaded_file, data_only=True, read_only=True)
        self.wb_form = openpyxl.load_workbook(uploaded_file, data_only=False, read_only=True)
        
        # 名前付き範囲の強行取得
        self.names_map = {}
        try:
            # defined_names 配下の定義を安全にスキャン
            for name, defn in self.wb_form.defined_names.items():
                # 参照先を取得（エラーが出やすい場所をtryで保護）
                try:
                    self.names_map[name] = list(defn.destinations)
                except:
                    self.names_map[name] = "Complex Formula / Unknown"
        except:
            st.error("名前定義の構造が複雑すぎるため、一部の解析をスキップします。")

    def get_val(self, sheet, addr):
        try: return self.wb_val[sheet][addr].value
        except: return 0.0

    def get_formula(self, sheet, addr):
        try: return self.wb_form[sheet][addr].value
        except: return "N/A"

# --- UI ---
st.title("🛡️ Gas Lab Engine : 名前の迷宮・強行突破 v17.2")

uploaded_file = st.file_uploader("算定Excelをアップロード", type=["xlsx"])

if uploaded_file:
    engine = GasLogicEngine(uploaded_file)
    
    # 最終数値
    final_cost = engine.get_val("別表4,5", "I56")
    vol_yakkan = engine.get_val("販売量", "O8")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("総括原価 (I56)", f"¥{final_cost:,.0f}")
    c2.metric("約款販売量 (O8)", f"{vol_yakkan:,.1f} m3")
    c3.metric("確定供給単価", f"{(final_cost/vol_yakkan if vol_yakkan else 0):,.2f} 円/m3")

    # 名前付き範囲の「中身」を強制表示
    st.subheader("🕵️ 抽出された名前定義（名前付き範囲）")
    if engine.names_map:
        name_data = []
        for name, dest in engine.names_map.items():
            # destinations から座標を特定
            ref_str = ""
            val = "N/A"
            if isinstance(dest, list):
                for s, c in dest:
                    ref_str += f"{s}!{c} "
                    val = engine.get_val(s, c.replace('$', ''))
            
            name_data.append({"名前": name, "参照座標": ref_str, "現在の値": val})
        
        st.table(pd.DataFrame(name_data))
    else:
        st.warning("名前付き範囲が検出されませんでした。シートの構成を確認してください。")

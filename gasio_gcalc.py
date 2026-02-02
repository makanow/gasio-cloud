import streamlit as st
import openpyxl # 数式抽出のためにopenpyxlを使用

st.title("🧪 Gas Lab Engine : ロジック自動解析モード")

uploaded_file = st.file_uploader("解析対象のExcelをアップロード", type=["xlsx"])

if uploaded_file:
    # data_only=False で読み込むことで「数式」を取得する
    wb = openpyxl.load_workbook(uploaded_file, data_only=False)
    
    st.success("Excelの全ロジックをスキャン中...")
    
    # ターゲットとなる主要な集計範囲
    target_sheets = ["ナビ", "販売量", "標準係数B", "総括原価"] # 想定されるシート名
    
    for sheet_name in wb.sheetnames:
        if any(target in sheet_name for target in target_sheets):
            with st.expander(f"🔍 シート「{sheet_name}」の計算ロジック"):
                ws = wb[sheet_name]
                # データの入っている範囲の数式を抽出
                for row in ws.iter_rows(min_row=1, max_row=50, min_col=1, max_col=15):
                    for cell in row:
                        if cell.value and str(cell.value).startswith('='):
                            st.code(f"セル {cell.coordinate}: {cell.value}")

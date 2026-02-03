import json
import streamlit as st
import pandas as pd

from calc.parser import load_entry_xlsx
from calc.masters import get_masters
from calc.model_2a import compute_2a
from calc.report_2a import build_report_2a

st.set_page_config(page_title='G-Calc v2 (2_a一致)', layout='wide')

st.title('G-Calc v2：様式第2 第1表（総原価整理表） 一致')


st.markdown("""
- エントリー専用.xlsx をアップロードし、**様式第2 第1表（総原価整理表）**を計算します。
- **A,B,C…の算出過程（式・参照入力・丸め）**を表示し、ブラックボックス化しません。
- 出力は **現行Excel（2_a）の見た目に完全準拠した帳票（Excel）**としてダウンロードできます。
- アップロードファイルはサーバに保存しません（セッション内のみ）。
""")

with st.expander('テンプレート', expanded=False):
    st.download_button('エントリー専用テンプレート（v1）をダウンロード',
                       data=open('G-Calc_entry_template_v1.xlsx','rb').read(),
                       file_name='G-Calc_entry_template_v1.xlsx')

uploaded = st.file_uploader('エントリー専用.xlsx をアップロード', type=['xlsx'])

if not uploaded:
    st.info('代表ケースの数値が入った G-Calc_entry_template_v1.xlsx をアップロードしてください。')
    st.stop()

entry = load_entry_xlsx(uploaded.getvalue())

pref = str(entry.basic.get('prefecture', '北海道'))
masters = get_masters(pref)

form2_1, trace, computed = compute_2a(entry, masters)

st.subheader('様式第2 第1表（計算結果）')
show = form2_1.rows.copy()
show['金額(円)'] = show['金額(円)'].map(lambda x: f"{x:,.0f}")
show['構成比(%)'] = show['構成比(%)'].map(lambda x: f"{x:,.1f}")
st.dataframe(show, use_container_width=True, hide_index=True)

c1,c2,c3 = st.columns(3)
c1.metric('ガスの販売量（㎥/年）', f"{form2_1.sales_m3:,.1f}")
c2.metric('合計（総原価）（円）', f"{computed['total_cost']:,.0f}")
c3.metric('1㎥当たり単価（円/㎥）', f"{computed['unit_yen_per_m3']:.2f}")

st.divider()
st.subheader('算出過程（トレース：A,B,C…）')
tdf = pd.DataFrame(trace.as_dict())
st.dataframe(tdf[['key','title','formula','value','unit','notes']], use_container_width=True, hide_index=True)

with st.expander('トレース詳細（参照入力）', expanded=False):
    st.json(trace.as_dict())

st.divider()
st.subheader('代表ケース一致チェック（北海道）')
expected = json.load(open('reference_case_hokkaido.json','r',encoding='utf-8'))

check_rows=[]
for k,v in expected.items():
    if k not in computed:
        continue
    got = computed[k]
    tol = 0.01 if isinstance(v,float) else 0.5
    ok = (abs(float(got) - float(v)) < tol)
    check_rows.append({'キー':k,'期待値':v,'計算値':got,'一致':ok})
chk = pd.DataFrame(check_rows)
st.dataframe(chk, use_container_width=True, hide_index=True)

st.divider()
st.subheader('申請向け帳票（Excel：見た目完全準拠 2_a）')
tpl = open('templates/report_template_2a.xlsx','rb').read()
out_bytes = build_report_2a(tpl, computed)
st.download_button('様式第2第1表（Excel）をダウンロード', data=out_bytes,
                   file_name='様式第2_第1表_総原価整理表.xlsx',
                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

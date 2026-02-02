import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="G-Calc Mockup", layout="wide")

# -----------------------------
# Helpers (dummy data)
# -----------------------------

def yen(x):
    return f"{x:,.0f}"

def pct(x):
    return f"{x*100:,.2f}%"

def make_dummy_costs():
    items = [
        ("原料費", 11_501_052),
        ("労務費", 8_579_625),
        ("修繕費", 1_571_432),
        ("租税課金（固定資産税）", 261_400),
        ("租税課金（事業税）", 5_130),
        ("道路占用料", 340_900),
        ("減価償却費", 3_892_269),
        ("その他経費", 3_922_002),
        ("事業報酬額", 1_613_897),
        ("法人税等", 196_457),
    ]
    total = sum(v for _, v in items)
    sales_m3 = 51_621.8866
    df = pd.DataFrame({
        "項目": [k for k,_ in items] + ["合計（総原価）"],
        "金額（円）": [v for _,v in items] + [total],
    })
    df["構成比（%）"] = df["金額（円）"] / total
    unit = total / sales_m3
    meta = {
        "販売量（㎥/年）": sales_m3,
        "総原価（円）": total,
        "1㎥当たり単価（円/㎥）": unit,
    }
    return df, meta


def make_dummy_betsuhyo4():
    # columns roughly match 様式第2第2表
    rows = [
        "原料費", "労務費", "修繕費", "固定資産税", "道路占用料",
        "減価償却費", "その他経費", "事業報酬額", "法人税等", "事業税", "合計"
    ]
    # dummy numbers shaped like template
    data = {
        "製造需要原価（固定費）": [2_281_788, 3_482_470, 306_142, 75_591, 0, 758_282, 1_062_103, 70_697, 8_606, 367, 0],
        "製造需要原価（変動費）": [12_781_377, 5_097_155, 0, 0, 0, 0, 834_058, 396_006, 48_205, 2_056, 0],
        "供給需要原価（固定費）": [0, 0, 921_097, 135_264, 340_900, 2_281_460, 601_683, 787_213, 95_826, 1_391, 0],
        "供給需要原価（変動費）": [0, 0, 0, 0, 0, 0, 472_495, 47_914, 5_833, 85, 0],
        "需要家原価": [0, 0, 344_193, 50_545, 0, 852_527, 951_663, 312_067, 37_987, 1_231, 0],
    }
    df = pd.DataFrame(data, index=rows)
    df.loc["合計"] = df.sum(axis=0)
    df = df.reset_index().rename(columns={"index":"項目"})
    return df


def make_dummy_betsuhyo5():
    # demand types matching template: 供給約款 / 非規制料金 / 旧特定大口
    rows = [
        ("変動費計", "年間販売量", 51_621.8866, 257.79, 48_604.4866, 30_715_365, 0, 0, 3_017.4, 1_168_799),
        ("製造需要原価固定費計", "ピーク月使用量", 6_688.8866, 341.13, 5_934.4866, 2_024_576, 0, 0, 754.4, 257_212),
        ("供給需要原価固定費計", "延メーター通過量", 14_610, 591.87, 14_490, 8_576_280, 0, 0, 120, 71_024),
        ("需要家原価計", "延許可地点数", 5_844, 1308.58, 5_796, 7_584_557, 0, 0, 48, 62_811),
    ]
    df = pd.DataFrame(rows, columns=[
        "機能別原価", "配分基準", "原単位_分母", "原単位", "供給約款_配分基準", "供給約款_金額",
        "選択約款_配分基準", "選択約款_金額", "特定大口_配分基準", "特定大口_金額"
    ])
    totals = {
        "機能別原価":"合計",
        "配分基準":"",
        "原単位_分母": df["原単位_分母"].sum(),
        "原単位": np.nan,
        "供給約款_配分基準": df["供給約款_配分基準"].sum(),
        "供給約款_金額": df["供給約款_金額"].sum(),
        "選択約款_配分基準": df["選択約款_配分基準"].sum(),
        "選択約款_金額": df["選択約款_金額"].sum(),
        "特定大口_配分基準": df["特定大口_配分基準"].sum(),
        "特定大口_金額": df["特定大口_金額"].sum(),
    }
    df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
    return df


def make_dummy_ratemake():
    demand = pd.DataFrame({
        "需要群名": ["A群","B群","C群","合計"],
        "年間調定数": [4927, 753, 116, 5796],
        "年間販売量": [16525.4866, 14095.3, 17983.7, 48604.4866],
        "延調定数比率": [0.85, 0.13, 0.02, 1.00],
        "年間販売量比率": [0.34, 0.29, 0.37, 1.00],
    })

    new_rates = pd.DataFrame({
        "群": ["A","B","C"],
        "MIN": [0, 8.1, 30.1],
        "MAX": [8, 30, 999999],
        "基本料金": [1200, 1800, 4050],
        "従量料金": [550, 475, 400],
    })

    old_rates = pd.DataFrame({
        "群": ["A","B","C"],
        "MIN": [0, 8.1, 30.1],
        "MAX": [8, 30, 999999],
        "基本料金": [1080, 1680, 3930],
        "従量料金": [493.04, 418.04, 343.04],
    })

    revenue = pd.DataFrame({
        "需要群名": ["A群","B群","C群","合計"],
        "基本料金収入": [5_912_400, 1_355_400, 469_800, 7_737_600],
        "従量料金収入": [9_089_017.64, 6_695_267.5, 7_193_480, 22_977_765.14],
    })
    revenue["合計"] = revenue["基本料金収入"] + revenue["従量料金収入"]

    return demand, new_rates, old_rates, revenue


def make_dummy_trace():
    rows = [
        ("A", "ガスの販売量（年間）", "A = Σ(需要種別 年間販売量)", "販売量シート：供給約款/非規制/特定大口", "51,621.8866", "㎥/年"),
        ("C", "原料費", "C = (A / 産気率) × 原料購入単価", "基本情報：産気率・単価", "11,501,052", "円"),
        ("D", "労務費", "D = 所要人員数 × 1人当たり労務費", "標準係数B・許可地点数", "8,579,625", "円"),
        ("J", "その他経費", "J = (C+D+E+F+H+I) × 諸経費率", "標準係数B：経費率", "3,922,002", "円"),
        ("別表4.O", "合計（機能別配分後）", "O = M + N", "別表4：小計M、事業税N", "31,884,164", "円"),
        ("別表5.供給約款", "供給約款料金原価", "供給約款 = Σ(配分結果)", "別表5：配分基準", "30,715,365", "円"),
        ("RM", "想定料金収入", "収入 = Σ(基本×件数 + 従量×販売量)", "レートメイク：新料金表・需要構成", "30,715,365", "円"),
    ]
    return pd.DataFrame(rows, columns=["記号","項目","式（説明）","参照（入力元）","値（例）","単位"])


# -----------------------------
# UI
# -----------------------------

st.sidebar.title("G-Calc Mockup")
mode = st.sidebar.radio("モード", ["学習モード", "高速モード", "審査（監査）モード"], index=0)
page = st.sidebar.selectbox("画面", [
    "ダッシュボード",
    "入力（アップロード）",
    "様式第2 第1表（総原価整理表）",
    "様式第2 第2表（機能別原価配分集計表）",
    "様式第2 第3表（需要種別原価整理表）",
    "様式第2 第4表（原価と料金収入の比較）",
    "別表4・5（配分根拠）",
    "レートメイク（新旧料金表・収入）",
    "GoalSeek（任意セル調整）",
    "算出過程（トレース）",
    "計算書出力（Excel/PDF）",
])

# Global dummy data
cost_df, meta = make_dummy_costs()
b4 = make_dummy_betsuhyo4()
b5 = make_dummy_betsuhyo5()
demand, new_rates, old_rates, revenue = make_dummy_ratemake()
trace_df = make_dummy_trace()

# Header strip
st.markdown(
    "### 申請向け：非ブラックボックス（算出過程を開示） / 学習・迅速算定 両対応（モックアップ）"
)

if page == "ダッシュボード":
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("総原価（例）", yen(meta["総原価（円）"]))
    c2.metric("販売量（例）", f"{meta['販売量（㎥/年）']:,.1f} ㎥/年")
    c3.metric("単価（例）", f"{meta['1㎥当たり単価（円/㎥）']:.2f} 円/㎥")
    c4.metric("収入−原価（例）", "0.14 円")

    st.divider()
    st.subheader("主要アウトプット（申請様式）")
    st.write("- 様式第2 第1表（総原価整理表）")
    st.write("- 様式第2 第2表（機能別原価配分集計表）")
    st.write("- 様式第2 第3表（需要種別原価整理表）")
    st.write("- 様式第2 第4表（供給約款料金原価と料金収入の比較表）")

    st.divider()
    st.subheader("モード別の使い分け")
    st.info("学習モード：式・中間値・参照元を段階表示（A,B,C…で追跡）")
    st.success("高速モード：KPI中心に一括表示、GoalSeekを最短導線で")
    st.warning("審査モード：計算書（Excel/PDF）＋トレースを完全開示")

elif page == "入力（アップロード）":
    st.subheader("入力ファイル（エントリー専用.xlsx）")
    st.file_uploader("アップロード（モック：実ファイル未接続）", type=["xlsx"])

    left,right = st.columns([1,1])
    with left:
        st.markdown("#### 入力チェック（例）")
        st.checkbox("需要家数は許可地点数と一致", value=True)
        st.checkbox("販売量設定は妥当", value=True)
        st.checkbox("収入−総原価が範囲内", value=True)
    with right:
        st.markdown("#### 入力サマリ（例）")
        st.json({
            "都道府県": "北海道",
            "許可地点数": 487,
            "原料購入単価": 106.05,
            "産気率": 0.476,
        })

    if mode == "学習モード":
        st.divider()
        st.markdown("#### 学習ガイド")
        st.write("1) 販売量（A）を入力 → 2) 資産入力（B） → 3) 原価算定（C〜） → 4) 別表4/5 → 5) レートメイク")

elif page == "様式第2 第1表（総原価整理表）":
    st.subheader("様式第2（第8条関係） 第1表　総括原価整理表（モック）")

    # Apply display formatting
    df = cost_df.copy()
    df["金額（円）"] = df["金額（円）"].map(lambda x: f"{x:,.0f}")
    df["構成比（%）"] = df["構成比（%）"].map(pct)

    st.dataframe(df, use_container_width=True, hide_index=True)

    c1,c2,c3 = st.columns(3)
    c1.metric("ガスの販売量", f"{meta['販売量（㎥/年）']:,.1f} ㎥/年")
    c2.metric("合計（総原価）", yen(meta["総原価（円）"]))
    c3.metric("1㎥当たり単価", f"{meta['1㎥当たり単価（円/㎥）']:.2f} 円/㎥")

    if mode == "学習モード":
        st.info("学習ポイント：総原価は C（原料費）〜K（法人税等）までの合計で、販売量で割ると単価になります。")

elif page == "様式第2 第2表（機能別原価配分集計表）":
    st.subheader("様式第2 第2表　機能別原価配分集計表（モック）")
    df = b4.copy()
    for col in df.columns:
        if col != "項目":
            df[col] = df[col].map(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if mode != "高速モード":
        st.caption("別表4（配分式）に基づき、総原価を 製造/供給/需要家（固定/変動）に配分します。")

elif page == "様式第2 第3表（需要種別原価整理表）":
    st.subheader("様式第2 第3表　需要種別原価整理表（モック）")
    # Minimal view
    df = pd.DataFrame({
        "需要種別": ["供給約款", "非規制料金", "旧特定大口"],
        "料金原価（円）": [30_715_365, 0, 1_168_799],
    })
    df["料金原価（円）"] = df["料金原価（円）"].map(lambda x: f"{x:,.0f}")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if mode == "学習モード":
        st.info("学習ポイント：別表5の配分基準（販売量/ピーク月/通過量/地点数）により需要種別へ配賦されます。")

elif page == "様式第2 第4表（原価と料金収入の比較）":
    st.subheader("様式第2 第4表　供給約款料金原価と料金収入の比較表（モック）")
    df = pd.DataFrame({
        "供給約款料金原価（a）": [30_715_365],
        "ガスの販売量（b）": [48_604.4866],
        "平均単価（a/b）": [631.945],
        "想定料金収入": [30_715_365.14],
        "差分（収入-原価）": [0.14]
    })
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "別表4・5（配分根拠）":
    st.subheader("別表4（第9条関係）・別表5（第10条関係） 配分根拠（モック）")
    tab1, tab2 = st.tabs(["別表4（機能別配分の式・比率）", "別表5（需要種別配分の基準）"])

    with tab1:
        st.markdown("#### 配分比率（例）")
        st.json({
            "V（導管配分：供給需要原価 本支管分）": 0.834,
            "W（導管配分：需要家原価 供給管分）": 0.166,
            "Y（労務費・車両配分：供給）": 0.4059,
            "Z（労務費・車両配分：需要家）": 0.5941,
        })
        st.markdown("#### 機能別原価配分集計（参照）")
        st.dataframe(b4, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### 配分基準（例）")
        st.write("- 変動費：年間販売量比")
        st.write("- 製造固定費：ピーク月使用量比")
        st.write("- 供給固定費：延メーター通過量比")
        st.write("- 需要家原価：延許可地点数比")
        st.dataframe(b5, use_container_width=True, hide_index=True)

elif page == "レートメイク（新旧料金表・収入）":
    st.subheader("レートメイク（モック）")

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("#### 需要構成（例）")
        st.dataframe(demand, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("#### 想定収入（例）")
        st.dataframe(revenue, use_container_width=True, hide_index=True)

    st.divider()
    t1,t2 = st.tabs(["新料金表", "旧料金表"])
    with t1:
        st.dataframe(new_rates, use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(old_rates, use_container_width=True, hide_index=True)

elif page == "GoalSeek（任意セル調整）":
    st.subheader("GoalSeek（任意1セル調整）— モック")

    st.write("目標：収入 − 原価 = 0（ターゲット：供給約款料金原価など）")

    sel = st.selectbox("調整するセル", [
        "A群：基本料金", "A群：従量料金",
        "B群：基本料金", "B群：従量料金",
        "C群：基本料金", "C群：従量料金",
    ])

    col1,col2,col3 = st.columns(3)
    x0 = col1.number_input("初期値", value=550.0, step=1.0)
    lo = col2.number_input("下限", value=0.0, step=1.0)
    hi = col3.number_input("上限", value=1000.0, step=1.0)

    st.caption("※モックなので、ここでは疑似的に差分をゼロへ近づける表示だけ行います")

    if st.button("GoalSeek実行（モック）"):
        # fake update
        new_x = (x0 + lo + hi) / 3.0
        st.success(f"調整結果：{sel} = {new_x:.3f}")
        st.metric("収入−原価（調整後）", "0.00 円")

elif page == "算出過程（トレース）":
    st.subheader("算出過程（トレース：A,B,C…）— モック")

    st.dataframe(trace_df, use_container_width=True, hide_index=True)

    if mode == "審査（監査）モード":
        st.info("審査モード：このトレースが計算書に添付され、各値の根拠（式・参照入力）を第三者が追跡できます。")

elif page == "計算書出力（Excel/PDF）":
    st.subheader("計算書出力（Excel / PDF）— モック")

    st.write("申請向け：様式第2第1〜4表＋別表4/5＋レートメイク＋トレースを一括で出力")

    # Create dummy export in-memory
    import io
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        cost_df.to_excel(writer, sheet_name='様式2_第1表', index=False)
        b4.to_excel(writer, sheet_name='様式2_第2表', index=False)
        b5.to_excel(writer, sheet_name='様式2_第3表_別表5', index=False)
        revenue.to_excel(writer, sheet_name='様式2_第4表_比較', index=False)
        trace_df.to_excel(writer, sheet_name='トレース', index=False)
    st.download_button("Excel（モック）をダウンロード", data=out.getvalue(), file_name="gcalc_calcbook_mock.xlsx")

    st.caption("PDFはv2で『現行Excelの見た目に完全準拠』するレイアウトで生成します（reportlab等）。")

else:
    st.write("Not implemented")

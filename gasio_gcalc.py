import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master: 投資算定プロト", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産算定エンジン")

EXCEL_FILE = "G-Calc_master.xlsx"

# 資産項目と標準係数Aの列位置（0始まりのインデックス）
# 1:ID, 2:開始, 3:終了, 4:建物, 5:構築物, 6:集合装置, 7:容器, 8:DKK, 9:DPK, 10:DKT, 11:DPT, 12:メーター, 13:備品...
ASSET_INFO = {
    "建物": {"code": "TTM", "col": 4, "rate": 0.03},
    "構築物": {"code": "KCB", "col": 5, "rate": 0.1},
    "集合装置": {"code": "SGS", "col": 6, "rate": 0.1},
    "容器": {"code": "YKI", "col": 7, "rate": 0.167},
    "導管・鋼管共同": {"code": "DKK", "col": 8, "rate": 0.077},
    "導管・ＰＥ共同": {"code": "DPK", "col": 9, "rate": 0.077},
    "導管・鋼管単独": {"code": "DKT", "col": 10, "rate": 0.077},
    "導管・ＰＥ単独": {"code": "DPT", "col": 11, "rate": 0.077},
    "メーター": {"code": "MTR", "col": 12, "rate": 0.077},
    "備品": {"code": "BHN", "col": 13, "rate": 0.2},
    "強制気化装置": {"code": "KKS", "col": 17, "rate": 0.1}
}

# ---------------------------------------------------------
# 2. マスタと期間判定ロジック
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        # Excelから27列のデータを読み込む (見出し3行を飛ばす)
        df = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
        
        # 2列目(index 1)に「HK」が含まれる行（期間データ）のみ抽出
        master = df[df.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        
        # 27列分の名前を強制割り当て
        master.columns = [f"Col{i}" for i in range(len(master.columns))]
        
        # 日付型に変換 (Col2:適用開始, Col3:適用終了)
        master['Col2'] = pd.to_datetime(master['Col2'])
        master['Col3'] = pd.to_datetime(master['Col3'])
        return master
    except Exception as e:
        st.error(f"マスタ読み込み失敗：{e}")
        return pd.DataFrame()

infra_master = load_infra_master()

def find_period_info(target_date):
    """取得年月日から、適用期間の名称と単価データを特定する"""
    if infra_master.empty:
        return "期間データなし", {}
    dt = pd.to_datetime(target_date)
    # 期間内に合致する行を探す
    match = infra_master[(infra_master['Col2'] <= dt) & (infra_master['Col3'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        label = f"{row['Col2'].strftime('%Y/%m/%d')} 〜 {row['Col3'].strftime('%Y/%m/%d')}"
        return label, row.to_dict()
    # 合致しない場合は最新の期間を返す
    last = infra_master.iloc[-1]
    label = f"{last['Col2'].strftime('%Y/%m/%d')} 〜 {last['Col3'].strftime('%Y/%m/%d')}"
    return label, last.to_dict()

# ---------------------------------------------------------
# 3. メインUI
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体設定")
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1, format="%d")

st.header("🏗️ 償却資産・分散取得入力")
st.write("「取得年月日」を入力すると、その時期に適用される標準単価が自動で適用されます。")

# 初期データのセット
if 'invest_data' not in st.session_state:
    st.session_state.invest_data = [
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "減免対象": False, "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "減免対象": True, "算出方式": "標準係数", "実績投資額": 0},
        {"項目": "メーター", "地点数": total_customers, "取得年月日": datetime(2020, 1, 1).date(), "減免対象": False, "算出方式": "標準係数", "実績投資額": 0},
    ]

# 入力エディタ
edited_rows = st.data_editor(
    st.session_state.invest_data,
    num_rows="dynamic",
    column_config={
        "項目": st.column_config.SelectboxColumn("項目", options=list(ASSET_INFO.keys())),
        "取得年月日": st.column_config.DateColumn("取得年月日"),
        "算出方式": st.column_config.SelectboxColumn("算出方式", options=["標準係数", "実績値"]),
        "実績投資額": st.column_config.NumberColumn("実績値入力 (円)"),
        "減免対象": st.column_config.CheckboxColumn("固定資産税減免"),
    },
    use_container_width=True
)

# ---------------------------------------------------------
# 4. 計算実行
# ---------------------------------------------------------
st.divider()
results = []
for row in edited_rows:
    p_label, p_data = find_period_info(row["取得年月日"])
    info = ASSET_INFO[row["項目"]]
    unit_price = p_data.get(f"Col{info['col']}", 0)
    
    # 投資額の算出（標準係数 or 実績値）
    if row["算出方式"] == "実績値":
        invest_base = row["実績投資額"]
    else:
        invest_base = row["地点数"] * unit_price
        
    # 投資額①（通常）と②（減免）の振り分け
    inv1 = 0 if row["減免対象"] else invest_base
    inv2 = invest_base if row["減免対象"] else 0
    dep = invest_base * info["rate"]
    
    results.append({
        "項目": row["項目"],
        "取得時期": p_label,
        "地点数": row["地点数"],
        "投資額①": inv1,
        "投資額②": inv2,
        "減価償却費": dep,
        "code": info["code"]
    })

res_df = pd.DataFrame(results)

# ---------------------------------------------------------
# 5. 結果表示とバリデーション
# ---------------------------------------------------------
st.subheader("📊 算定結果サマリー")
if not res_df.empty:
    st.dataframe(res_df.drop(columns=["code"]), use_container_width=True)

    # 厳格な検算
    st.subheader("🔍 整合性チェック（バリデーション）")
    c1, c2 = st.columns(2)
    
    # 導管グループの合計チェック (DKK, DPK, DKT, DPT)
    pipe_codes = ["DKK", "DPK", "DKT", "DPT"]
    pipe_sum = res_df[res_df["code"].isin(pipe_codes)]["地点数"].sum()
    
    with c1:
        if pipe_sum == total_customers:
            st.success(f"✅ 導管グループ合計：{pipe_sum} / {total_customers} (一致)")
        else:
            st.error(f"❌ 導管グループ合計：{pipe_sum} (目標値: {total_customers})")
            
    with c2:
        for cat in ["建物", "メーター"]:
            cat_sum = res_df[res_df["項目"] == cat]["地点数"].sum()
            if cat_sum == total_customers:
                st.success(f"✅ {cat}合計：{cat_sum} (一致)")
            else:
                st.warning(f"⚠️ {cat}合計：{cat_sum} (ズレあり)")

    # 投資額の集計
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("有形固定資産 投資額①", f"{res_df['投資額①'].sum():,.0f} 円")
    m2.metric("有形固定資産 投資額②", f"{res_df['投資額②'].sum():,.0f} 円")
    m3.metric("総 減価償却費", f"{res_df['減価償却費'].sum():,.0f} 円")

import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# ---------------------------------------------------------
# 1. Excel互換の端数処理関数 (四捨五入エンジン)
# ---------------------------------------------------------
def excel_round(value, decimals=0):
    """ExcelのROUND関数と同じ挙動（四捨五入）をする"""
    if pd.isna(value): return 0
    d = Decimal(str(value))
    exp = Decimal('1') if decimals == 0 else Decimal('0.' + '0' * (decimals - 1) + '1')
    return float(d.quantize(exp, rounding=ROUND_HALF_UP))

# ---------------------------------------------------------
# 2. 初期設定
# ---------------------------------------------------------
st.set_page_config(page_title="G-Calc Master: 完全検算版", layout="wide")
st.title("🛡️ G-Calc Cloud: 投資・償却資産算定エンジン（Excel完全互換）")

EXCEL_FILE = "G-Calc_master.xlsx"

ASSET_INFO = {
    "建物": {"code": "TTM", "col": 3, "rate": 0.03},
    "構築物": {"code": "KCB", "col": 4, "rate": 0.1},
    "集合装置": {"code": "SGS", "col": 5, "rate": 0.1},
    "容器": {"code": "YKI", "col": 6, "rate": 0.167},
    "導管・鋼管共同": {"code": "DKK", "col": 7, "rate": 0.077},
    "導管・ＰＥ共同": {"code": "DPK", "col": 8, "rate": 0.077},
    "導管・鋼管単独": {"code": "DKT", "col": 9, "rate": 0.077},
    "導管・ＰＥ単独": {"code": "DPT", "col": 10, "rate": 0.077},
    "メーター": {"code": "MTR", "col": 11, "rate": 0.077},
    "備品": {"code": "BHN", "col": 12, "rate": 0.2},
    "強制気化装置": {"code": "KKS", "col": 16, "rate": 0.1},
    "集合装置・バルク": {"code": "SSB", "col": 14, "rate": 0.1}
}

EXEMPT_CODES = ["SGS", "DKK", "DPK", "DKT", "DPT", "SSB"]
EXEMPT_LIMIT_DATE = datetime(2017, 4, 1).date()

# ---------------------------------------------------------
# 3. マスタ読込
# ---------------------------------------------------------
@st.cache_data
def load_infra_master():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='標準係数A', skiprows=2, header=None)
        master = df[df.iloc[:, 1].astype(str).str.contains("HK", na=False)].copy()
        master = master.iloc[:, 1:].reset_index(drop=True)
        def fix_date(val):
            v_str = str(val).split(' ')[0]
            return pd.Timestamp("2100-12-31") if "9999" in v_str else pd.to_datetime(v_str, errors='coerce')
        master['start_dt'] = master.iloc[:, 1].apply(fix_date)
        master['end_dt'] = master.iloc[:, 2].apply(fix_date)
        return master
    except Exception as e:
        st.error(f"マスタ読込失敗：{e}")
        return pd.DataFrame()

infra_master = load_infra_master()

def find_period_info(target_date):
    if infra_master.empty or target_date is None: return "日付未入力", None
    dt = pd.to_datetime(target_date)
    match = infra_master[(infra_master['start_dt'] <= dt) & (infra_master['end_dt'] >= dt)]
    if not match.empty:
        row = match.iloc[0]
        return f"{row['start_dt'].strftime('%Y/%m/%d')} 〜 {row['end_dt'].strftime('%Y/%m/%d')}", row
    last = infra_master.iloc[-1]
    return f"{last['start_dt'].strftime('%Y/%m/%d')} 〜 {last['end_dt'].strftime('%Y/%m/%d')}", last

# ---------------------------------------------------------
# 4. メインUI：エディタ
# ---------------------------------------------------------
st.sidebar.header("⚙️ 全体設定")
total_customers = st.sidebar.number_input("許可地点数", value=245, step=1, format="%d")

st.header("🏗️ 償却資産入力：分散取得明細")

if 'invest_df' not in st.session_state:
    st.session_state.invest_df = pd.DataFrame([
        {"項目": "建物", "地点数": total_customers, "取得年月日": datetime(1983, 1, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免しない"},
        {"項目": "導管・ＰＥ共同", "地点数": total_customers, "取得年月日": datetime(2015, 4, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免する"},
        {"項目": "メーター", "地点数": total_customers, "取得年月日": datetime(2020, 1, 1).date(), "算出方式": "標準係数", "実績投資額": 0, "減免適用": "減免しない"},
    ])

# 【エディタのカンマ設定】 format="%,d" を指定
edited_df = st.data_editor(
    st.session_state.invest_df,
    num_rows="dynamic",
    column_config={
        "項目": st.column_config.SelectboxColumn("項目", options=list(ASSET_INFO.keys())),
        "取得年月日": st.column_config.DateColumn("取得年月日"),
        "算出方式": st.column_config.SelectboxColumn("方式", options=["標準係数", "実績値"]),
        "実績投資額": st.column_config.NumberColumn("実績値(円)", format="%,d"),
        "減免適用": st.column_config.SelectboxColumn("減免適用", options=["減免する", "減免しない"]),
        "地点数": st.column_config.NumberColumn("地点数", format="%,d"),
    },
    use_container_width=True
)
st.session_state.invest_df = edited_df

# ---------------------------------------------------------
# 5. 計算（Excel流の「は数」処理）
# ---------------------------------------------------------
results = []
for index, row in edited_df.iterrows():
    if row["取得年月日"] is None or pd.isna(row["取得年月日"]):
        results.append({"項目": row["項目"], "取得時期": "⚠️日付入力待ち", "地点数": row["地点数"], "投資額①": 0, "投資額②": 0, "判定助言": "－", "減価償却費": 0, "code": "ERR"})
        continue

    p_label, p_data = find_period_info(row["取得年月日"])
    info = ASSET_INFO.get(row["項目"], {"code": "UNKNOWN", "col": 3, "rate": 0})
    
    # 自動判定アドバイス
    is_recommend = (row["取得年月日"] <= EXEMPT_LIMIT_DATE) and (info["code"] in EXEMPT_CODES)
    advice = "💡推奨(要申請)" if is_recommend else "非対象"

    # 投資額算出（Excel互換四捨五入）
    if row["算出方式"] == "実績値":
        invest_base = excel_round(row["実績投資額"], 0)
    else:
        unit_price = p_data.iloc[info["col"]] if p_data is not None else 0
        invest_base = excel_round(row["地点数"] * unit_price, 0)
    
    # 振り分け
    is_exempt = (row["減免適用"] == "減免する")
    inv1 = 0 if is_exempt else invest_base
    inv2 = invest_base if is_exempt else 0
    
    # 償却費算出（Excel同様、小数点第1位まで）
    dep = excel_round(invest_base * info["rate"], 1)
    
    results.append({
        "項目": row["項目"], "取得時期": p_label, "地点数": row["地点数"], 
        "投資額①": inv1, "投資額②": inv2, "判定助言": advice,
        "減価償却費": dep, "code": info["code"]
    })

res_df = pd.DataFrame(results)

# ---------------------------------------------------------
# 6. 表示（徹底的なカンマ区切り）
# ---------------------------------------------------------
st.divider()
if not res_df.empty:
    st.subheader("📊 算定結果サマリー (桁区切り表示)")
    
    # Dataframeの表示もカンマと¥マークを強制
    st.dataframe(
        res_df.drop(columns=["code"]),
        column_config={
            "投資額①": st.column_config.NumberColumn("投資額①(通常)", format="¥%,d"),
            "投資額②": st.column_config.NumberColumn("投資額②(減免)", format="¥%,d"),
            "減価償却費": st.column_config.NumberColumn("減価償却費", format="¥%,.1f"),
            "地点数": st.column_config.NumberColumn("地点数", format="%,d"),
        },
        use_container_width=True
    )

    # 最終集計メトリクス（ここもカンマ付き）
    st.divider()
    m1, m2, m3 = st.columns(3)
    # 合計を計算
    sum_inv1 = res_df['投資額①'].sum()
    sum_inv2 = res_df['投資額②'].sum()
    sum_dep = res_df['減価償却費'].sum()
    
    m1.metric("投資額① (非減免合計)", f"¥ {sum_inv1:,.0f}")
    m2.metric("投資額② (減免合計)", f"¥ {sum_inv2:,.0f}")
    m3.metric("総 減価償却費", f"¥ {sum_dep:,.1f}")

# ---------------------------------------------------------
# 7. 検算バリデーション
# ---------------------------------------------------------
st.subheader("🔍 整合性検算")
pipe_sum = res_df[res_df["code"].isin(["DKK", "DPK", "DKT", "DPT"])]["地点数"].sum()
if pipe_sum == total_customers:
    st.success(f"✅ 導管合計：{pipe_sum:,} / {total_customers:,} (一致)")
else:
    st.error(f"❌ 導管合計：{pipe_sum:,} (目標：{total_customers:,} / 不足：{total_customers - pipe_sum:,})")

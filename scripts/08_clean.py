"""第 4 步：清洗。只删完全重复行，其余一律加标记列。口径见 docs/口径与决策.md。
在项目根目录运行：
    python scripts/08_clean.py
输出：data/clean_lines.csv（每行一条原始记录 + 标记列）
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online_retail_II.csv"
OUT = ROOT / "data" / "clean_lines.csv"

# 第 3 步定稿的非商品编码清单；gift_ 开头的礼品卡另外判断
NON_PRODUCT = {"POST", "DOT", "C2", "C3", "BANK CHARGES", "AMAZONFEE", "CRUK", "ADJUST", "ADJUST2",
               "B", "S", "TEST001", "TEST002", "M", "m", "D", "GIFT"}

df = pd.read_csv(SRC, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"])
n_raw = len(df)

# ---------- 1. 删除完全重复行（除 Sheet 外所有字段相同，保留第一条）----------
cols = [c for c in df.columns if c != "Sheet"]
d = df[~df.duplicated(subset=cols)].copy().reset_index(drop=True)

# ---------- 2. 基础标记 ----------
d["Amount"] = d["Quantity"] * d["Price"]
d["InvoiceDay"] = d["InvoiceDate"].dt.normalize()
d["is_cancel"] = d["Invoice"].str.startswith("C")
d["has_customer"] = d["Customer ID"].notna()
d["is_product"] = ~d["StockCode"].isin(NON_PRODUCT) & ~d["StockCode"].str.startswith("gift_")

finance_adj = d["Price"] < 0
stock_book = ~d["is_cancel"] & (d["Quantity"] <= 0) & (d["Price"] == 0) & ~d["has_customer"]
review = ~d["is_cancel"] & (d["Quantity"] <= 0) & ~stock_book & ~finance_adj

# 每行一个主标签，按优先级从上到下取第一个符合的
d["row_label"] = "商品销售"
d.loc[d["Price"] == 0, "row_label"] = "0元行"
d.loc[d["is_cancel"], "row_label"] = "取消"
d.loc[~d["is_product"], "row_label"] = "非商品"
d.loc[review, "row_label"] = "待核查异常"
d.loc[stock_book, "row_label"] = "库存记账"
d.loc[finance_adj, "row_label"] = "财务调整"

# ---------- 3. 付费购买行，以及"整单取消配对" ----------
d["is_paid_purchase"] = (~d["is_cancel"] & d["is_product"] & d["has_customer"]
                         & (d["Quantity"] > 0) & (d["Price"] > 0))

# 同一客户、同一商品、数量正好相反、同一天：购买行与其后的取消行按时间顺序一一配对
# 跨天的取消当作退货，只冲减金额，不影响有效购买日
key = ["Customer ID", "StockCode", "absQty", "InvoiceDay"]
buy = d[d["is_paid_purchase"]].assign(absQty=lambda x: x["Quantity"])
cxl = d[d["is_cancel"] & d["is_product"] & d["has_customer"]].assign(absQty=lambda x: -x["Quantity"])
buy = buy.sort_values("InvoiceDate").assign(k=lambda x: x.groupby(key).cumcount())
cxl = cxl.sort_values("InvoiceDate").assign(k=lambda x: x.groupby(key).cumcount())
pairs = buy.reset_index().merge(cxl.reset_index(), on=key + ["k"], suffixes=("_buy", "_cxl"))
pairs = pairs[pairs["InvoiceDate_cxl"] >= pairs["InvoiceDate_buy"]]

d["cancel_matched"] = False
d.loc[pairs["index_buy"], "cancel_matched"] = True
d.loc[pairs["index_cxl"], "cancel_matched"] = True

# 有效购买行：付费购买且没被配对取消；某客户某天有至少一条有效购买行，这一天就是有效购买日
d["valid_purchase_line"] = d["is_paid_purchase"] & ~d["cancel_matched"]
day_valid = d.groupby(["Customer ID", "InvoiceDay"])["valid_purchase_line"].transform("any")
d["is_valid_purchase_day"] = d["has_customer"] & day_valid.eq(True)

# ---------- 4. 输出 ----------
d.to_csv(OUT, index=False, encoding="utf-8-sig")


# ---------- 5. 对账：和第 3 步记录的数字逐项比较 ----------
def check(name, actual, expected=None):
    mark = "" if expected is None else ("  ✓" if actual == expected else f"  ✗ 期望 {expected:,}")
    print(f"{name:<34}{actual:>12,}{mark}")


print("== 对账 ==")
check("原始行数", n_raw, 1_067_371)
check("删除的完全重复行", n_raw - len(d), 34_335)
check("清洗后行数", len(d), 1_033_036)
check("缺失 Customer ID", int((~d["has_customer"]).sum()), 235_151)
check("C 取消单行", int(d["is_cancel"].sum()), 19_104)
check("库存记账", int(stock_book.sum()), 3_393)
check("待核查异常", int(review.sum()), 0)
check("财务调整（Price < 0）", int(finance_adj.sum()), 5)
check("缺失 Description", int(d["Description"].isna().sum()), 4_275)
check("非商品行（新清单）", int((~d["is_product"]).sum()))

print("\n== 主标签分布 ==")
print(d.groupby("row_label").agg(行数=("Amount", "size"), 金额合计=("Amount", "sum")).round(2).to_string())

print("\n== 整单取消配对 ==")
print(f"同一天配对数：{len(pairs):,}，涉及客户 {pairs['Customer ID'].nunique():,} 个")
cust_days = d[d["is_paid_purchase"]].groupby(["Customer ID", "InvoiceDay"])
lost = (cust_days["is_valid_purchase_day"].any() == False).sum()  # noqa: E712
print(f"因配对而不再算有效购买日的客户-日期：{lost:,}")
print("配对样例（前 8 对）：")
print(pairs[["Customer ID", "StockCode", "absQty", "Invoice_buy", "InvoiceDate_buy",
             "Invoice_cxl", "InvoiceDate_cxl"]].head(8).to_string())

print("\n== 客户分析范围 ==")
vd = d[d["is_valid_purchase_day"]].drop_duplicates(["Customer ID", "InvoiceDay"])
print(f"有至少 1 个有效购买日的客户：{vd['Customer ID'].nunique():,}")
print(f"有效购买日（客户-日期）总数：{len(vd):,}")
print(f"\n已保存：{OUT}")

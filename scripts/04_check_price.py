"""第 3 步：细看价格为 0 或负数的行（不含已标为"非客户交易的库存记账"的 3,393 行）。只统计，不修改数据。
在项目根目录运行：
    python scripts/04_check_price.py
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
SHOW = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Sheet"]

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online_retail_II.csv"


def sample(title, rows, k=8):
    print(f"  ▶ 样例：{title}（共 {len(rows):,} 行）")
    print(rows[SHOW].head(k).to_string() if len(rows) else "  （无）", "\n")


df = pd.read_csv(SRC, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"])
cols = [c for c in df.columns if c != "Sheet"]
d = df[~df.duplicated(subset=cols)].copy()

is_c = d["Invoice"].str.startswith("C")
no_id = d["Customer ID"].isna()
stock_book = ~is_c & (d["Quantity"] <= 0) & (d["Price"] == 0) & no_id  # 上一个决定已标记的行

p0 = d[(d["Price"] == 0) & ~stock_book]
pneg = d[d["Price"] < 0]

print(f"Price = 0 的行（不含库存记账 {stock_book.sum():,} 行）：{len(p0):,}")
print(f"Price < 0 的行：{len(pneg):,}\n")

print("== 1. Price = 0 的其余行：发票类型 × 数量正负 × 是否有客户编号 ==")
print(pd.crosstab(
    [p0["Invoice"].str[0].where(p0["Invoice"].str[0].isin(["C", "A"]), "普通"),
     (p0["Quantity"] > 0).map({True: "数量>0", False: "数量≤0"})],
    p0["Customer ID"].isna().map({True: "无客户编号", False: "有客户编号"})), "\n")

with_id = p0[p0["Customer ID"].notna()]
print("== 2. Price = 0 且有客户编号的行：涉及多少客户、多少天 ==")
print(f"行数 {len(with_id):,}，客户数 {with_id['Customer ID'].nunique():,}，"
      f"客户-日期组合数 {with_id.groupby(['Customer ID', with_id['InvoiceDate'].dt.date]).ngroups:,}")
print("描述出现次数前 15：")
print(with_id["Description"].value_counts(dropna=False).head(15).to_string(), "\n")

# 关键：这些"客户-日期"当天有没有其他正常付费商品？没有的话，单靠 0 元行就会多出一个"有效购买日"
paid = d[~is_c & (d["Quantity"] > 0) & (d["Price"] > 0) & d["Customer ID"].notna()]
paid_days = set(zip(paid["Customer ID"], paid["InvoiceDate"].dt.date))
keys = list(zip(with_id["Customer ID"], with_id["InvoiceDate"].dt.date))
only_free = [k not in paid_days for k in keys]
print("== 3. 这些 0 元行所在的客户-日期，当天是否还有正常付费购买 ==")
print(f"当天有付费购买：{len(keys) - sum(only_free):,} 行")
print(f"当天只有 0 元行：{sum(only_free):,} 行，涉及客户-日期 {len(set(k for k, f in zip(keys, only_free) if f)):,} 个\n")

sample("Price = 0、有客户编号", with_id)
sample("Price = 0、有客户编号、当天只有 0 元行", with_id[only_free])
sample("Price = 0、无客户编号、数量>0", p0[p0["Customer ID"].isna() & (p0["Quantity"] > 0)])
sample("Price < 0", pneg)

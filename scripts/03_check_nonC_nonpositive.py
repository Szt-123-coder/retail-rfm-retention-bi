"""第 3 步：细看"非 C 发票、数量 ≤ 0"的行。只统计和打印样例，不修改数据。
在项目根目录运行：
    python scripts/03_check_nonC_nonpositive.py
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
SHOW = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Sheet"]

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online_retail_II.csv"

# 初步关键词，看完下面第 3 部分的描述清单后再决定要不要增减
KEYWORDS = ["short", "lost", "mixed"]


def sample(title, rows, k=8):
    print(f"  ▶ 样例：{title}（共 {len(rows):,} 行）")
    print(rows[SHOW].head(k).to_string() if len(rows) else "  （无）", "\n")


df = pd.read_csv(SRC, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"])
cols = [c for c in df.columns if c != "Sheet"]
d = df[~df.duplicated(subset=cols)].copy()  # 按已定口径去重

g = d[~d["Invoice"].str.startswith("C") & (d["Quantity"] <= 0)].copy()
g["Amount"] = g["Quantity"] * g["Price"]
no_id = g["Customer ID"].isna()
price0 = g["Price"] == 0
desc = g["Description"].fillna("").str.lower()
has_kw = desc.str.contains("|".join(KEYWORDS))

print(f"非 C 发票、数量 ≤ 0 的行：{len(g):,}\n")

print("== 1. 数量 = 0 与 数量 < 0 分开统计 ==")
print(f"数量 = 0：{(g['Quantity'] == 0).sum():,} 行，金额合计 {g.loc[g['Quantity'] == 0, 'Amount'].sum():,.2f}")
print(f"数量 < 0：{(g['Quantity'] < 0).sum():,} 行，金额合计 {g.loc[g['Quantity'] < 0, 'Amount'].sum():,.2f}\n")

print("== 2. 价格是否为 0 × 是否有客户编号 ==")
print(pd.crosstab(price0.map({True: "Price=0", False: "Price≠0"}),
                  no_id.map({True: "无客户编号", False: "有客户编号"})), "\n")

print("== 3. Price=0 且无客户编号的行：描述出现次数前 30（含空描述） ==")
print(g.loc[price0 & no_id, "Description"].value_counts(dropna=False).head(30).to_string(), "\n")

print(f"== 4. 按你的规则分组（关键词：{KEYWORDS}） ==")
stock_adj = price0 & no_id & has_kw
review = ~stock_adj
print(f"疑似库存调整：{stock_adj.sum():,} 行")
print(f"待核查异常：  {review.sum():,} 行")
print(f"  其中 有客户编号：            {(review & ~no_id).sum():,}")
print(f"  其中 价格不为 0：            {(review & ~price0).sum():,}")
print(f"  其中 Price=0、无编号但描述不含关键词或为空：{(review & price0 & no_id).sum():,}\n")

sample("疑似库存调整", g[stock_adj])
sample("待核查：有客户编号", g[review & ~no_id])
sample("待核查：价格不为 0", g[review & ~price0])
sample("待核查：Price=0、无编号、描述不含关键词", g[review & price0 & no_id])

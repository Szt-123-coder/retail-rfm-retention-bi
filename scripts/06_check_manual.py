"""第 3 步：细看 StockCode 为 M / m（Manual，手工录入）的行。只统计，不修改数据。
在项目根目录运行：
    python scripts/06_check_manual.py
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
SHOW = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID"]

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online_retail_II.csv"


def sample(title, rows, k=8):
    print(f"  ▶ 样例：{title}（共 {len(rows):,} 行）")
    print(rows[SHOW].head(k).to_string() if len(rows) else "  （无）", "\n")


df = pd.read_csv(SRC, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"])
cols = [c for c in df.columns if c != "Sheet"]
d = df[~df.duplicated(subset=cols)].copy()
d["Amount"] = d["Quantity"] * d["Price"]
d["is_c"] = d["Invoice"].str.startswith("C")

m = d[d["StockCode"].isin(["M", "m"])].copy()
print(f"M / m 行：{len(m):,}\n")

print("== 1. 取消单与否 × 是否有客户编号：行数和金额 ==")
print(m.groupby([m["is_c"].map({True: "C 取消单", False: "普通发票"}),
                 m["Customer ID"].notna().map({True: "有客户编号", False: "无客户编号"})])
      .agg(行数=("Amount", "size"), 金额合计=("Amount", "sum")).round(2).to_string(), "\n")

print("== 2. 单价分布 ==")
print(m["Price"].describe().round(2).to_string())
print("最常见单价：")
print(m["Price"].value_counts().head(10).to_string(), "\n")

# 同一张发票里还有没有正常商品行？有的话 M 更像"给这张单补价/改价"，没有的话更像单独一笔
other = d[~d["StockCode"].isin(["M", "m"])].groupby("Invoice").size()
m["同票有其他行"] = m["Invoice"].map(other).fillna(0) > 0
print("== 3. M 行所在发票里是否还有其他编码的行 ==")
print(m["同票有其他行"].value_counts().rename({True: "有", False: "只有 M"}).to_string(), "\n")

print("== 4. 金额最大的 5 行和最小的 5 行 ==")
print(m.sort_values("Amount")[SHOW + ["Amount"]].tail(5).to_string())
print(m.sort_values("Amount")[SHOW + ["Amount"]].head(5).to_string(), "\n")

sample("普通发票、有客户编号", m[~m["is_c"] & m["Customer ID"].notna()])
sample("C 取消单、有客户编号", m[m["is_c"] & m["Customer ID"].notna()])
sample("发票里只有 M 行", m[~m["同票有其他行"]])

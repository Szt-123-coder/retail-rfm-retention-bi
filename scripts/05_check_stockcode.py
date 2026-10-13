"""第 3 步：列出所有"不是 5 位数字开头"的 StockCode，人工判断哪些是非商品。只统计，不修改数据。
在项目根目录运行：
    python scripts/05_check_stockcode.py
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 40)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online_retail_II.csv"

df = pd.read_csv(SRC, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"])
cols = [c for c in df.columns if c != "Sheet"]
d = df[~df.duplicated(subset=cols)].copy()
d["Amount"] = d["Quantity"] * d["Price"]

odd = d[~d["StockCode"].str.match(r"^\d{5}")]
print(f"不是 5 位数字开头的行：{len(odd):,}，不同编码：{odd['StockCode'].nunique():,}\n")

# 每个编码一行：行数、有客户编号的行数、金额合计、最常见描述
summary = odd.groupby("StockCode").agg(
    行数=("Invoice", "size"),
    有客户编号行数=("Customer ID", lambda s: s.notna().sum()),
    金额合计=("Amount", "sum"),
    最常见描述=("Description", lambda s: s.mode().iat[0] if s.notna().any() else None),
).sort_values("行数", ascending=False)

print("== 1. 每个编码的概况（按行数排序）==")
print(summary.round(2).to_string(), "\n")

# 编码长相分组：纯字母 / 字母+数字 / 其他，帮助看规律
def shape(code):
    if code.isalpha():
        return "纯字母"
    if code[:1].isalpha() and any(ch.isdigit() for ch in code):
        return "字母开头含数字"
    return "其他"

print("== 2. 按编码长相分组 ==")
print(summary.groupby(summary.index.map(shape))["行数"].agg(["count", "sum"])
      .rename(columns={"count": "编码数", "sum": "行数"}).to_string(), "\n")

print("== 3. 「字母开头含数字」的编码，各取 3 行原始样例 ==")
for code in [c for c in summary.index if shape(c) == "字母开头含数字"][:10]:
    rows = odd[odd["StockCode"] == code]
    print(f"  ▶ {code}（{len(rows):,} 行）")
    print(rows[["Invoice", "Description", "Quantity", "Price", "Customer ID"]].head(3).to_string(), "\n")

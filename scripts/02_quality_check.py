"""第 3 步：数据质量检查。只统计条数，不修改任何数据。
先运行 01_xlsx_to_csv.py 生成 data/online_retail_II.csv，再在项目根目录运行：
    python scripts/02_quality_check.py
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
SHOW = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Sheet"]


def sample(title, rows, k=6):
    """打印几行原始样例，先看数据长什么样，再做判断"""
    print(f"  ▶ 样例：{title}")
    print(rows[SHOW].head(k).to_string(), "\n")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online_retail_II.csv"

df = pd.read_csv(SRC, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"])
cols = [c for c in df.columns if c != "Sheet"]  # 判断重复时不看来源工作表
n = len(df)


def show(name, count, base=n):
    print(f"{name:<40}{count:>10,}  ({count / base:6.2%})")


print(f"总行数：{n:,}")
print(df["Sheet"].value_counts().to_string(), "\n")

# 1. 重复行：8 个字段完全相同
dup = df.duplicated(subset=cols)
dup_in_sheet = df.duplicated(subset=cols + ["Sheet"])
show("1 完全重复行（合计）", dup.sum())
show("  其中：同一工作表内重复", dup_in_sheet.sum())
show("  其中：两表重叠造成的重复", (dup & ~dup_in_sheet).sum())
overlap = df[(df["Sheet"] == "Year 2010-2011") & (df["InvoiceDate"] <= df.loc[df["Sheet"] == "Year 2009-2010", "InvoiceDate"].max())]
sample("同一工作表内的重复（相邻两行是一对）",
       df[df.duplicated(subset=cols + ["Sheet"], keep=False)].sort_values(cols))
sample("两表重叠造成的重复（同一行出现在两个工作表）",
       df[(dup & ~dup_in_sheet) | df.duplicated(subset=cols, keep="last") & ~df.duplicated(subset=cols + ["Sheet"], keep="last")].sort_values(cols))
print(f"  两表重叠时段：{overlap['InvoiceDate'].min()} 至 {overlap['InvoiceDate'].max()}，第二张表在该时段有 {len(overlap):,} 行\n")

d = df[~dup].copy()  # 以下各项在去掉完全重复行之后统计
m = len(d)
print(f"去重后行数：{m:,}\n")

is_c = d["Invoice"].str.startswith("C")
is_product = d["StockCode"].str.match(r"^\d{5}")
d["Amount"] = d["Quantity"] * d["Price"]

# 2. 缺客户编号
no_cust = d["Customer ID"].isna()
show("2 缺 Customer ID 的行", no_cust.sum(), m)
sample("缺 Customer ID", d[no_cust])
pos_sales = d[~is_c & (d["Quantity"] > 0) & (d["Price"] > 0)]
share = pos_sales.loc[pos_sales["Customer ID"].isna(), "Amount"].sum() / pos_sales["Amount"].sum()
print(f"  占正常销售额的比例：{share:.1%}\n")

# 3. 取消单
show("3 取消单行（Invoice 以 C 开头）", is_c.sum(), m)
show("  取消单里数量 > 0 的行", (is_c & (d["Quantity"] > 0)).sum(), m)
show("  非取消单但数量 <= 0 的行", (~is_c & (d["Quantity"] <= 0)).sum(), m)
sample("取消单", d[is_c])
sample("非取消单但数量 <= 0", d[~is_c & (d["Quantity"] <= 0)])

# 4. 价格异常
show("4 单价 = 0 的行", (d["Price"] == 0).sum(), m)
show("  单价 < 0 的行", (d["Price"] < 0).sum(), m)
sample("单价 = 0", d[d["Price"] == 0])
sample("单价 < 0", d[d["Price"] < 0])

# 5. 非商品行
show("5 非商品行（StockCode 不以 5 位数字开头）", (~is_product).sum(), m)
top = (d[~is_product].groupby("StockCode")
       .agg(行数=("Amount", "size"), 金额合计=("Amount", "sum"), 说明=("Description", "first"))
       .sort_values("行数", ascending=False).head(10))
print(top.to_string(), "\n")

# 6. 缺商品描述
show("6 缺 Description 的行", d["Description"].isna().sum(), m)
sample("缺 Description", d[d["Description"].isna()])

# 7. 极端数量
show("7 |数量| >= 10,000 的行", (d["Quantity"].abs() >= 10000).sum(), m)
print(d.loc[d["Quantity"].abs() >= 10000, ["Invoice", "StockCode", "Description", "Quantity", "Price", "Customer ID", "InvoiceDate"]].to_string(), "\n")

# 8. 净额为负的客户（商品行、有客户编号）
net = d[is_product & ~no_cust].groupby("Customer ID")["Amount"].sum()
print(f"8 商品净额 < 0 的客户：{(net < 0).sum():,} / {len(net):,}")

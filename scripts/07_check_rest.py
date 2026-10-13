"""第 3 步：最后三类——缺失描述、极端数量、净商品金额为负的客户。只统计，不修改数据。
在项目根目录运行：
    python scripts/07_check_rest.py
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)
SHOW = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID"]

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online_retail_II.csv"

# 第 3 步定稿的非商品清单（见 docs/口径与决策.md）
NON_PRODUCT = {"POST", "DOT", "C2", "C3", "BANK CHARGES", "AMAZONFEE", "CRUK", "ADJUST", "ADJUST2",
               "B", "S", "TEST001", "TEST002", "M", "m", "D", "GIFT"}

df = pd.read_csv(SRC, dtype={"Invoice": str, "StockCode": str}, parse_dates=["InvoiceDate"])
cols = [c for c in df.columns if c != "Sheet"]
d = df[~df.duplicated(subset=cols)].copy()
d["Amount"] = d["Quantity"] * d["Price"]
d["is_c"] = d["Invoice"].str.startswith("C")
d["has_id"] = d["Customer ID"].notna()
d["is_product"] = ~d["StockCode"].isin(NON_PRODUCT) & ~d["StockCode"].str.startswith("gift_")

# ---------- 1. 缺失描述 ----------
nd = d[d["Description"].isna()]
print(f"== 1. 缺失 Description：{len(nd):,} 行 ==")
print(pd.crosstab((nd["Price"] == 0).map({True: "Price=0", False: "Price≠0"}),
                  nd["has_id"].map({True: "有客户编号", False: "无客户编号"})))
print(f"其中会进入客户分析的（商品行、有客户编号、Price>0）：{(nd['is_product'] & nd['has_id'] & (nd['Price'] > 0)).sum():,} 行\n")

# ---------- 2. 极端数量 ----------
big = d[d["Quantity"].abs() >= 10000].sort_values("InvoiceDate")
print(f"== 2. |Quantity| ≥ 10,000：{len(big):,} 行（全部列出）==")
print(big[SHOW + ["Amount"]].to_string(), "\n")

# 有没有对应的取消行：同客户、同商品、数量正好相反
pos = big[big["Quantity"] > 0]
neg = d[d["is_c"]][["Customer ID", "StockCode", "Quantity", "Invoice", "InvoiceDate"]]
pairs = pos.merge(neg.assign(Quantity=-neg["Quantity"]), on=["Customer ID", "StockCode", "Quantity"],
                  suffixes=("", "_取消"))
print("正数量的大单里，能找到「同客户、同商品、数量相反」取消行的：")
print(pairs[["Invoice", "InvoiceDate", "StockCode", "Quantity", "Customer ID", "Invoice_取消", "InvoiceDate_取消"]]
      .to_string() if len(pairs) else "  （无）", "\n")

# ---------- 3. 净商品金额为负的客户 ----------
p = d[d["is_product"] & d["has_id"]]
net = p.groupby("Customer ID")["Amount"].sum()
neg_ids = net[net < 0].index
print(f"== 3. 两年净商品金额 < 0 的客户：{len(neg_ids):,} 个（有客户编号的客户共 {net.size:,} 个）==")
first_buy = p[~p["is_c"] & (p["Quantity"] > 0)].groupby("Customer ID")["InvoiceDate"].min()
first_c = p[p["is_c"]].groupby("Customer ID")["InvoiceDate"].min()
info = pd.DataFrame({"净额": net[neg_ids].round(2),
                     "首次购买": first_buy.reindex(neg_ids),
                     "首次取消": first_c.reindex(neg_ids)})
info["先取消后购买或从未购买"] = info["首次购买"].isna() | (info["首次取消"] < info["首次购买"])
print(info.sort_values("净额").to_string(), "\n")
print("「先取消后购买或从未购买」的客户数：", int(info["先取消后购买或从未购买"].sum()))

worst = info["净额"].idxmin()
print(f"\n  ▶ 净额最低的客户 {worst:.0f} 的全部商品行（前 10 行）")
print(p[p["Customer ID"] == worst].sort_values("InvoiceDate")[SHOW].head(10).to_string())

# 15 取消画像：主窗口内每个客户的取消金额与取消占比，用来定电话回访门槛
# 运行：python scripts/15_cancel_profile.py（在项目根目录）
import pandas as pd

START, END = "2010-12-10", "2011-12-09"   # RFM 主窗口
df = pd.read_csv("data/clean_lines.csv", dtype={"Invoice": str, "StockCode": str},
                 usecols=["Invoice", "Customer ID", "InvoiceDay", "Amount", "row_label", "has_customer"])
w = df[df["has_customer"] & df["InvoiceDay"].between(START, END)]
cust = pd.read_csv("data/powerbi/customers.csv")[["Customer ID", "segment", "high_value", "M"]]

buy = w[w["row_label"] == "商品销售"].groupby("Customer ID")["Amount"].sum().rename("购买额")
can = w[w["row_label"] == "取消"].groupby("Customer ID").agg(
    取消金额=("Amount", lambda s: -s.sum()), 取消发票数=("Invoice", "nunique"))
t = cust.merge(buy, on="Customer ID", how="left").merge(can, on="Customer ID", how="left")
t[["取消金额", "取消发票数"]] = t[["取消金额", "取消发票数"]].fillna(0)
t["取消占比"] = t["取消金额"] / t["购买额"]          # 取消金额 ÷ 商品购买额（未扣取消）
c = t[t["取消金额"] > 0]

print(f"主窗口客户 {len(t)} 人，有取消记录 {len(c)} 人")
print("\n=== 1. 取消金额与取消占比的分布（有取消的人）===")
print(c[["取消金额", "取消占比", "取消发票数"]].describe(percentiles=[.25, .5, .75, .9, .95]).round(3))

print("\n=== 2. 不同门槛下各剩多少人 ===")
for amt in [100, 500, 1000]:
    for r in [0.1, 0.2, 0.3]:
        n = ((c["取消金额"] >= amt) & (c["取消占比"] >= r)).sum()
        print(f"取消金额 ≥ {amt:>5}  且  取消占比 ≥ {r:.0%}：{n} 人")

print("\n=== 3. 有取消的人按分层分布 ===")
print(c["segment"].value_counts())

print("\n=== 4. 取消金额最高的 10 人 ===")
print(c.sort_values("取消金额", ascending=False)
       [["Customer ID", "segment", "high_value", "购买额", "取消金额", "取消占比", "取消发票数"]]
       .head(10).round(3).to_string(index=False))

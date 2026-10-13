# 14 无客户编号行画像：对比有 / 无 Customer ID 的商品销售行，帮助推测缺 ID 的原因
# 运行：python scripts/14_no_id_profile.py（在项目根目录）
import pandas as pd

df = pd.read_csv("data/clean_lines.csv", dtype={"Invoice": str, "StockCode": str})
sales = df[df["row_label"] == "商品销售"].copy()   # 只看商品销售行（不含取消、非商品）
sales["组"] = sales["has_customer"].map({True: "有ID", False: "无ID"})

print("=== 1. 行数与销售额占比（商品销售行）===")
g = sales.groupby("组").agg(行数=("Amount", "size"), 销售额=("Amount", "sum"))
g["行数占比"] = (g["行数"] / g["行数"].sum()).round(4)
g["销售额占比"] = (g["销售额"] / g["销售额"].sum()).round(4)
print(g)

print("\n=== 2. 单张发票的样子（每张发票的行数、金额）===")
inv = sales.groupby(["组", "Invoice"]).agg(行数=("Amount", "size"), 金额=("Amount", "sum")).reset_index()
print(inv.groupby("组")[["行数", "金额"]].describe(percentiles=[.5]).round(1))

print("\n=== 3. 单行的数量与单价（中位数）===")
print(sales.groupby("组")[["Quantity", "Price"]].median())

print("\n=== 4. 国家分布（各组前 5，占本组行数比例）===")
for k, sub in sales.groupby("组"):
    print(k); print(sub["Country"].value_counts(normalize=True).head(5).round(4))

print("\n=== 5. 按月看无 ID 行占比（是不是某段时间突然变多）===")
sales["月"] = sales["InvoiceDay"].str[:7]
print(sales.groupby("月")["has_customer"].apply(lambda s: round(1 - s.mean(), 4)).to_string())

print("\n=== 6. 无 ID 原始样本（随机 10 行）===")
cols = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Country"]
print(sales[~sales["has_customer"]][cols].sample(10, random_state=1).to_string())

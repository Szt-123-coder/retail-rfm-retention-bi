# 16 README 数字核对：把 README 里引用的每个数字从数据重新算一遍并打印
# 运行：python scripts/16_readme_check.py（在项目根目录，先跑完 01、08、10–13）
import pandas as pd

D = "data/"
raw = pd.read_csv(D + "online_retail_II.csv", usecols=["Invoice"])
cl = pd.read_csv(D + "clean_lines.csv", dtype={"Invoice": str},
                 usecols=["Invoice", "Customer ID", "InvoiceDay", "Amount", "row_label", "has_customer", "is_valid_purchase_day"])
c = pd.read_csv(D + "powerbi/customers.csv")
m = pd.read_csv(D + "powerbi/migration.csv")
rep = pd.read_csv(D + "powerbi/repurchase.csv")
co = pd.read_csv(D + "powerbi/cohort.csv")
T = c["M"].sum()

def show(name, value): print(f"{name}: {value}")

print("=== 数据规模与清洗 ===")
show("原始行数", len(raw))
show("清洗后行数", len(cl))
show("删除的完全重复行", len(raw) - len(cl))
nid = (~cl["has_customer"]).sum()
show("无客户编号行 / 占比", f"{nid} / {nid / len(cl):.2%}")
s = cl[cl["row_label"] == "商品销售"]
share = s.loc[~s["has_customer"], "Amount"].sum() / s["Amount"].sum()
show("无客户编号商品销售额占比 / 有编号占比", f"{share:.2%} / {1 - share:.2%}")

print("\n=== 分层与价值 ===")
show("主窗口客户", len(c))
show("高价值人数 / M 占比", f"{c['high_value'].sum()} / {c.loc[c['high_value'], 'M'].sum() / T:.1%}")
core = c[c["segment"] == "核心活跃"]
show("核心活跃人数 / M 占比", f"{len(core)} / {core['M'].sum() / T:.1%}")
one = (c["F"] == 1).sum()
show("只有 1 个有效购买日", f"{one} / {one / len(c):.1%}")

print("\n=== 回购与留存 ===")
print(rep[rep["预热期（月）"] == 1].to_string(index=False))
f = co[co["cohort"] != "2009-12"]
agg = f.groupby("k")[["active", "size"]].sum()
w = agg["active"] / agg["size"]
show("首次观察客户加权留存 第1/6/12月", f"{w[1]:.1%} / {w[6]:.1%} / {w[12]:.1%}")

print("\n=== 迁移与名单 ===")
prev_hf = m[m["上一年分层"] == "高频待召回"]
gone = (prev_hf["主窗口分层"] == "主窗口无有效购买日").sum()
show("上一年高频待召回 / 主窗口未再买", f"{len(prev_hf)} / {gone} ({gone / len(prev_hf):.1%})")
gone_rate = (m["主窗口分层"] == "主窗口无有效购买日").groupby(m["上一年分层"]).agg(["sum", "count", "mean"])
print("各上一年分层主窗口未再买：\n" + gone_rate.to_string())
call = c[(c["segment"] == "高频待召回") & c["high_value"]]
show("召回名单 / 其中按规则流失", f"{len(call)} / {call['churned_by_rule'].sum()}")
mail1 = m[(m["主窗口分层"] == "主窗口无有效购买日") & m["上一年分层"].isin(["核心活跃", "高频待召回"])]
ids21 = [12755, 15749, 12931, 14607, 15482, 12454, 12607, 13680, 14146, 15514, 15298,
         14299, 16938, 14557, 15365, 16801, 16716, 14665, 17867, 17368, 14410]
mail2 = c[c["churned_by_rule"] & c["high_value"] & (c["segment"] == "低频沉睡") & ~c["Customer ID"].isin(ids21)]
show("邮件组（157 + 10）", f"{len(mail1)} + {len(mail2)} = {len(mail1) + len(mail2)}")

print("\n=== 核心活跃购买间隔 ===")
v = cl[cl["has_customer"] & cl["is_valid_purchase_day"] & cl["Customer ID"].isin(core["Customer ID"])]
v = v[["Customer ID", "InvoiceDay"]].drop_duplicates()
v["InvoiceDay"] = pd.to_datetime(v["InvoiceDay"])
gaps = v.sort_values(["Customer ID", "InvoiceDay"]).groupby("Customer ID")["InvoiceDay"].diff().dt.days.dropna()
show("间隔中位数 / 第75百分位", f"{gaps.median():.0f} / {gaps.quantile(.75):.0f}")

print("\n=== 流失阈值依据（所有客户相邻有效购买日间隔）===")
a = cl[cl["has_customer"] & cl["is_valid_purchase_day"]][["Customer ID", "InvoiceDay"]].drop_duplicates()
a["InvoiceDay"] = pd.to_datetime(a["InvoiceDay"])
g = a.sort_values(["Customer ID", "InvoiceDay"]).groupby("Customer ID")["InvoiceDay"].diff().dt.days.dropna()
show("间隔个数 / ≤180 天占比", f"{len(g)} / {(g <= 180).mean():.1%}")

# 17 行动名单：把第 6 步定下的各类名单合成一张表，供 Power BI 第 3 页使用。规则见 docs/口径与决策.md。
# 先运行 08、10、11、13，再在项目根目录运行：python scripts/17_action_list.py
import pandas as pd

START, END = "2010-12-10", "2011-12-09"          # RFM 主窗口
INTERNAL_CHECK = [16446, 12346]                    # 大额当天整单撤单，交内部核实
CANCEL_EXCLUDE = [16446]                           # 取消额全部来自那一单当天撤单，不进取消回访

c = pd.read_csv("data/powerbi/customers.csv")
m = pd.read_csv("data/powerbi/migration.csv")
prev = pd.read_csv("data/rfm_prev.csv")[["Customer ID", "M"]].rename(columns={"M": "上一年M"})
cl = pd.read_csv("data/clean_lines.csv", dtype={"Invoice": str},
                 usecols=["Customer ID", "InvoiceDay", "Amount", "row_label", "has_customer", "is_valid_purchase_day"])

# 取消金额与取消占比（主窗口，同 scripts/15）
w = cl[cl["has_customer"] & cl["InvoiceDay"].between(START, END)]
buy = w[w["row_label"] == "商品销售"].groupby("Customer ID")["Amount"].sum()
can = -w[w["row_label"] == "取消"].groupby("Customer ID")["Amount"].sum()
c["取消金额"] = c["Customer ID"].map(can).fillna(0).round(2)
c["取消占比"] = (c["取消金额"] / c["Customer ID"].map(buy)).round(4)

# 每个客户最后一个有效购买日（两年全量）
last = cl[cl["has_customer"] & cl["is_valid_purchase_day"]].groupby("Customer ID")["InvoiceDay"].max()

cols = ["Customer ID", "segment", "high_value", "churned_by_rule", "R", "M", "取消金额", "取消占比"]
parts = []

# 1 电话召回：高频待召回 × 高价值；先未按规则流失，再按 M 从高到低
a = c[(c["segment"] == "高频待召回") & c["high_value"]].sort_values(["churned_by_rule", "M"], ascending=[True, False])
parts.append(a[cols].assign(行动="电话召回", 行动顺序=1))

# 2 取消回访：取消金额 ≥ 500 且取消占比 ≥ 20%；按取消金额从高到低
b = c[(c["取消金额"] >= 500) & (c["取消占比"] >= 0.2) & ~c["Customer ID"].isin(CANCEL_EXCLUDE)]
parts.append(b.sort_values("取消金额", ascending=False)[cols].assign(行动="取消回访", 行动顺序=2))

# 3 邮件召回（a）：上一年核心活跃 / 高频待召回、主窗口无有效购买日；按上一年 M 从高到低
e1 = m[(m["主窗口分层"] == "主窗口无有效购买日") & m["上一年分层"].isin(["核心活跃", "高频待召回"])]
e1 = e1.merge(prev, on="Customer ID", how="left").sort_values("上一年M", ascending=False)
e1 = e1.rename(columns={"上一年分层": "segment"})[["Customer ID", "segment", "上一年M"]]
parts.append(e1.assign(行动="邮件召回", 行动顺序=3, 分层依据="上一年"))

# 3 邮件召回（b）：主窗口按规则流失的高价值低频沉睡，且不在取消回访名单
e2 = c[c["churned_by_rule"] & c["high_value"] & (c["segment"] == "低频沉睡") & ~c["Customer ID"].isin(b["Customer ID"])]
parts.append(e2.sort_values("M", ascending=False)[cols].assign(行动="邮件召回", 行动顺序=3))

# 4 内部核实：大额当天整单撤单
ic = pd.DataFrame({"Customer ID": INTERNAL_CHECK}).merge(c[cols], on="Customer ID", how="left")
parts.append(ic.assign(行动="内部核实", 行动顺序=4))

out = pd.concat(parts, ignore_index=True)
out["分层依据"] = out["分层依据"].fillna("主窗口")
out.loc[out["segment"].isna(), "segment"] = out["Customer ID"].map(m.set_index("Customer ID")["上一年分层"])
out.loc[out["分层依据"].eq("主窗口") & ~out["Customer ID"].isin(c["Customer ID"]), "分层依据"] = "上一年"
out["最后有效购买日"] = out["Customer ID"].map(last)
out["R"] = (pd.Timestamp("2011-12-10") - pd.to_datetime(out["最后有效购买日"])).dt.days  # 统一按截止日 2011-12-10
out["上一年M"] = out["Customer ID"].map(prev.set_index("Customer ID")["上一年M"])  # 上一年无有效购买日则为空
out["行动内序号"] = out.groupby("行动").cumcount() + 1
out = out.rename(columns={"segment": "分层", "high_value": "高价值", "churned_by_rule": "按规则流失", "M": "主窗口M"})
out = out[["行动顺序", "行动", "行动内序号", "Customer ID", "分层依据", "分层", "高价值", "按规则流失",
           "最后有效购买日", "R", "主窗口M", "上一年M", "取消金额", "取消占比"]]

assert out["Customer ID"].duplicated().sum() == 0, "同一客户出现在两个行动里"
out.to_csv("data/powerbi/actions.csv", index=False, encoding="utf-8-sig")

print("=== 各行动人数 ===")
print(out["行动"].value_counts().reindex(["电话召回", "取消回访", "邮件召回", "内部核实"]).to_string())
print("\n=== 每个行动前 3 行 ===")
print(out.groupby("行动顺序").head(3).to_string(index=False))

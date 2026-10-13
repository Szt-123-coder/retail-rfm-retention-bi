"""第 5 步：cohort 月留存、N 天回购率，以及 1/2/3 个月预热期的敏感性分析。口径见 docs/口径与决策.md。
先运行 08_clean.py，再在项目根目录运行：
    python scripts/12_cohort.py
输出：data/cohort_retention.csv（长表：首单月 × 第 k 月）
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "clean_lines.csv"
OUT = ROOT / "data" / "cohort_retention.csv"

LAST_DAY = pd.Timestamp("2011-12-09")
LAST_FULL_MONTH = pd.Period("2011-11", "M")
FIRST_MONTH = pd.Period("2009-12", "M")

d = pd.read_csv(SRC, usecols=["Customer ID", "InvoiceDay", "is_valid_purchase_day"], parse_dates=["InvoiceDay"])
days = (d[d["is_valid_purchase_day"]].drop_duplicates(["Customer ID", "InvoiceDay"])
        .sort_values(["Customer ID", "InvoiceDay"]))
days["month"] = days["InvoiceDay"].dt.to_period("M")
first_day = days.groupby("Customer ID")["InvoiceDay"].min()
days["cohort"] = days["Customer ID"].map(first_day).dt.to_period("M")

# ---------- 1. 月留存矩阵（预热期 1 个月：2009-12 为期初已观察客户）----------
c = days[(days["cohort"] <= LAST_FULL_MONTH) & (days["month"] <= LAST_FULL_MONTH)].copy()
c["k"] = (c["month"] - c["cohort"]).apply(lambda x: x.n)
active = c.drop_duplicates(["Customer ID", "k"]).groupby(["cohort", "k"]).size().rename("active")
size = c[c["k"] == 0].groupby("cohort")["Customer ID"].nunique().rename("size")
long = active.reset_index().merge(size.reset_index(), on="cohort")
long["rate"] = long["active"] / long["size"]
long["cohort_label"] = long["cohort"].astype(str).where(long["cohort"] != FIRST_MONTH, "2009-12（期初已观察客户）")
long.to_csv(OUT, index=False, encoding="utf-8-sig")

mat = long.pivot(index="cohort", columns="k", values="rate")
mat.insert(0, "人数", size)
print("== 1. 月留存率（%），行 = 首单月，列 = 第 k 月；k=0 恒为 100%；空白 = 尚不可观察 ==")
show = mat.copy()
show[mat.columns[1:]] = (mat[mat.columns[1:]] * 100).round(1)
print(show[["人数"] + list(range(0, 13))].to_string(), "\n")


# ---------- 2. 敏感性分析：预热期 1/2/3 个月 ----------
def weighted_rate(cohorts, k):
    """所有可观察到第 k 月的 cohort，按人数加权的第 k 月留存率"""
    sub = long[long["cohort"].isin(cohorts) & (long["k"] == k)]
    ok = [co for co in cohorts if co + k <= LAST_FULL_MONTH]
    n = size.reindex(ok).sum()
    return sub[sub["cohort"].isin(ok)]["active"].sum() / n if n else float("nan")


print("== 2. 敏感性分析：预热期取 1/2/3 个月时，首次观察客户的加权留存率 ==")
rows = []
for w in (1, 2, 3):
    start = FIRST_MONTH + w
    cohorts = [co for co in size.index if co >= start]
    rows.append({"预热期（月）": w, "首次观察起始月": str(start),
                 "期初已观察客户数": int(size[size.index < start].sum()),
                 "首次观察客户数": int(size.reindex(cohorts).sum()),
                 **{f"第{k}月留存": f"{weighted_rate(cohorts, k):.1%}" for k in (1, 3, 6, 12)}})
print(pd.DataFrame(rows).to_string(index=False), "\n")

# ---------- 3. N 天回购率（首次观察客户，敏感性同上）----------
days["nth"] = days.groupby("Customer ID").cumcount() + 1
second = days[days["nth"] == 2].set_index("Customer ID")["InvoiceDay"]
gap = (second.reindex(first_day.index) - first_day).dt.days  # 没有第 2 次的为 NaN

print("== 3. N 天回购率：分母 = 首次观察客户中首个有效购买日 ≤ 2011-12-09 − N；分子 = 其中 N 天内有第 2 个有效购买日 ==")
rows = []
for w in (1, 2, 3):
    start = (FIRST_MONTH + w).start_time
    for n in (30, 90, 180):
        end = LAST_DAY - pd.Timedelta(days=n)
        base = first_day[(first_day >= start) & (first_day <= end)].index
        hit = (gap.reindex(base) <= n).sum()
        rows.append({"预热期（月）": w, "N": n, "分母": len(base), "分子": int(hit), "回购率": f"{hit / len(base):.1%}"})
print(pd.DataFrame(rows).pivot(index="N", columns="预热期（月）", values="回购率").to_string())
print("\n（主口径：预热期 1 个月、N = 90；分母分子明细如下）")
nd = pd.DataFrame(rows)
print(nd[nd["预热期（月）"] == 1].to_string(index=False))
nd.to_csv(ROOT / "data" / "repurchase_n.csv", index=False, encoding="utf-8-sig")
print(f"\n已保存：{OUT}、data/repurchase_n.csv")

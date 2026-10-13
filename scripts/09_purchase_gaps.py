"""第 5 步（准备）：看相邻两个有效购买日之间隔多少天，用来定 N 天回购率的 N 和流失阈值。只统计，不修改数据。
先运行 08_clean.py，再在项目根目录运行：
    python scripts/09_purchase_gaps.py
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "clean_lines.csv"
WARMUP_END = pd.Timestamp("2010-01-01")  # 2009-12 为预热期，之后首次出现的是"首次观察客户"

d = pd.read_csv(SRC, usecols=["Customer ID", "InvoiceDay", "is_valid_purchase_day"], parse_dates=["InvoiceDay"])
days = (d[d["is_valid_purchase_day"]]
        .drop_duplicates(["Customer ID", "InvoiceDay"])
        .sort_values(["Customer ID", "InvoiceDay"]))
days["gap"] = days.groupby("Customer ID")["InvoiceDay"].diff().dt.days
days["nth"] = days.groupby("Customer ID").cumcount() + 1  # 第几个有效购买日

n_cust = days["Customer ID"].nunique()
n_repeat = (days.groupby("Customer ID").size() >= 2).sum()
print(f"有效购买日客户：{n_cust:,}；其中至少 2 个有效购买日：{n_repeat:,}（{n_repeat / n_cust:.1%}）\n")

PCTS = [0.25, 0.5, 0.75, 0.8, 0.9, 0.95]
CUTS = [30, 60, 90, 120, 180, 270, 365]


def describe(title, gaps):
    print(f"== {title}：{len(gaps):,} 个间隔 ==")
    print("分位数（天）：", "  ".join(f"P{int(p * 100)}={gaps.quantile(p):.0f}" for p in PCTS))
    print("累计占比：    ", "  ".join(f"≤{c}天 {(gaps <= c).mean():.1%}" for c in CUTS))
    bins = pd.cut(gaps, [0, 30, 60, 90, 120, 180, 270, 365, 800])
    print(bins.value_counts().sort_index().to_string(), "\n")


describe("1. 所有相邻有效购买日间隔", days["gap"].dropna())

# N 天回购率看的是"第 1 个到第 2 个有效购买日"，并且只算首次观察客户
first = days[days["nth"] == 1].set_index("Customer ID")["InvoiceDay"]
new_ids = first[first >= WARMUP_END].index
second_gap = days[(days["nth"] == 2) & days["Customer ID"].isin(new_ids)]["gap"]
print(f"首次观察客户（首个有效购买日在 2010-01-01 及以后）：{len(new_ids):,}，其中有第 2 个有效购买日：{len(second_gap):,}")
describe("2. 首次观察客户：第 1 → 第 2 个有效购买日", second_gap)

print("== 3. 随机 5 个复购客户的有效购买日序列（看真实长相）==")
sample_ids = days[days["nth"] == 3]["Customer ID"].sample(5, random_state=1)
for cid in sample_ids:
    s = days[days["Customer ID"] == cid]
    print(f"  客户 {cid:.0f}：", "，".join(f"{x:%Y-%m-%d}" for x in s["InvoiceDay"].head(8)),
          "…" if len(s) > 8 else "", f"（共 {len(s)} 天）")

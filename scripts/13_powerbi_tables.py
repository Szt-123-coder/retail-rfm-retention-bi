"""第 5 步：把 Power BI 要用的表整理到 data/powerbi/。先依次运行 08、10、11、12，再运行：
    python scripts/13_powerbi_tables.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "powerbi"
OUT.mkdir(exist_ok=True)
WARMUP_END = pd.Timestamp("2010-01-01")

# 客户表：主窗口 RFM + 上一年分层 + 首个有效购买日 + 客户类型
rfm = pd.read_csv(DATA / "rfm_main.csv", parse_dates=["last"])
mig = pd.read_csv(DATA / "segment_migration.csv")
d = pd.read_csv(DATA / "clean_lines.csv", usecols=["Customer ID", "InvoiceDay", "is_valid_purchase_day"],
                parse_dates=["InvoiceDay"])
first = d[d["is_valid_purchase_day"]].groupby("Customer ID")["InvoiceDay"].min().rename("first_valid_day")

cust = (rfm.merge(mig, on="Customer ID", how="left")
        .merge(first.reset_index(), on="Customer ID", how="left"))
cust["客户类型"] = cust["first_valid_day"].lt(WARMUP_END).map({True: "期初已观察客户", False: "首次观察客户"})
cust["Customer ID"] = cust["Customer ID"].astype(int)
cust = cust.rename(columns={"last": "last_valid_day"})
ORDER = ["核心活跃", "成长中", "近期仅一个有效购买日", "观望", "高频待召回", "低频沉睡"]
cust["segment_order"] = cust["segment"].map({s: i + 1 for i, s in enumerate(ORDER)})  # Power BI 里按此排序
cust.to_csv(OUT / "customers.csv", index=False, encoding="utf-8-sig")

# 迁移表：包含两个窗口里出现过的所有客户
mig["Customer ID"] = mig["Customer ID"].astype(int)
mig.to_csv(OUT / "migration.csv", index=False, encoding="utf-8-sig")

# cohort 长表：加上日历月，方便看"斜线"
co = pd.read_csv(DATA / "cohort_retention.csv")
co["calendar_month"] = (pd.PeriodIndex(co["cohort"], freq="M") + co["k"]).astype(str)
co.to_csv(OUT / "cohort.csv", index=False, encoding="utf-8-sig")

rep = pd.read_csv(DATA / "repurchase_n.csv")
rep.to_csv(OUT / "repurchase.csv", index=False, encoding="utf-8-sig")

print(f"customers.csv  {len(cust):,} 行（主窗口有有效购买日的客户）")
print(f"migration.csv  {len(mig):,} 行（两个窗口出现过的客户）")
print(f"cohort.csv     {len(co):,} 行")
print(f"repurchase.csv {len(rep):,} 行")
print("\n核对：")
print(f"  一次性客户占比（F = 1）：{(cust['F'] == 1).mean():.1%}")
print(f"  按规则流失：{int(cust['churned_by_rule'].sum()):,} 人")
print(f"  高频待召回且高价值：{int(((cust['segment'] == '高频待召回') & cust['high_value']).sum()):,} 人")
print(f"\n已保存到：{OUT}")

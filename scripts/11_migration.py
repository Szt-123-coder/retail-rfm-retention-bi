"""第 5 步：上一年窗口 RFM + 分层迁移（同一客户去年在哪层、今年在哪层）。
上一年 R、M 打分用主窗口的五分位切分点。先运行 08_clean.py、10_rfm.py，再运行：
    python scripts/11_migration.py
输出：data/rfm_prev.csv、data/segment_migration.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "clean_lines.csv"
MAIN = ROOT / "data" / "rfm_main.csv"

WINDOWS = {
    "上一年": (pd.Timestamp("2009-12-10"), pd.Timestamp("2010-12-09"), pd.Timestamp("2010-12-10")),
    "主窗口": (pd.Timestamp("2010-12-10"), pd.Timestamp("2011-12-09"), pd.Timestamp("2011-12-10")),
}
ORDER = ["核心活跃", "成长中", "近期仅一个有效购买日", "观望", "高频待召回", "低频沉睡"]

use = ["Customer ID", "InvoiceDay", "Amount", "is_product", "has_customer", "is_valid_purchase_day"]
d = pd.read_csv(SRC, usecols=use, parse_dates=["InvoiceDay"])
d = d[d["has_customer"]]


def raw_rfm(start, end, cutoff):
    w = d[(d["InvoiceDay"] >= start) & (d["InvoiceDay"] <= end)]
    days = w[w["is_valid_purchase_day"]].drop_duplicates(["Customer ID", "InvoiceDay"])
    rf = days.groupby("Customer ID")["InvoiceDay"].agg(last="max", F="size")
    rf["R"] = (cutoff - rf["last"]).dt.days
    m = w[w["is_product"]].groupby("Customer ID")["Amount"].sum().rename("M")
    return rf.join(m, how="left").fillna({"M": 0})


def segment(r, f):
    if r >= 4:
        return "核心活跃" if f >= 4 else ("成长中" if f >= 2 else "近期仅一个有效购买日")
    if r == 3:
        return "观望"
    return "高频待召回" if f >= 3 else "低频沉睡"


main = raw_rfm(*WINDOWS["主窗口"])
_, r_edges = pd.qcut(main["R"], 5, retbins=True)
_, m_edges = pd.qcut(main["M"], 5, retbins=True)
r_bins = [-np.inf, *r_edges[1:-1], np.inf]
m_bins = [-np.inf, *m_edges[1:-1], np.inf]
print("主窗口切分点 R（天）：", [round(x) for x in r_edges[1:-1]])
print("主窗口切分点 M（£）：", [round(x, 2) for x in m_edges[1:-1]], "\n")


def score(rfm):
    rfm["R_score"] = pd.cut(rfm["R"], r_bins, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F_score"] = pd.cut(rfm["F"], [0, 1, 2, 4, 9, np.inf], labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M_score"] = pd.cut(rfm["M"], m_bins, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["segment"] = [segment(r, f) for r, f in zip(rfm["R_score"], rfm["F_score"])]
    return rfm


main = score(main)
prev = score(raw_rfm(*WINDOWS["上一年"]))

# 核对：主窗口用切分点重打的分，应和 10_rfm.py 的结果完全一致
check = pd.read_csv(MAIN).set_index("Customer ID")["segment"]
print("核对主窗口分层与 rfm_main.csv 一致：", bool((main["segment"] == check.reindex(main.index)).all()), "\n")

print("== 1. 两个窗口各层人数（同一套切分点）==")
cnt = pd.DataFrame({"上一年": prev["segment"].value_counts(), "主窗口": main["segment"].value_counts()}).reindex(ORDER)
cnt.loc["合计"] = cnt.sum()
print(cnt.to_string(), "\n")

mig = pd.DataFrame({"上一年分层": prev["segment"], "主窗口分层": main["segment"]})
mig["上一年分层"] = mig["上一年分层"].fillna("上一年无有效购买日")
mig["主窗口分层"] = mig["主窗口分层"].fillna("主窗口无有效购买日")
rows = ORDER + ["上一年无有效购买日"]
cols = ORDER + ["主窗口无有效购买日"]

print("== 2. 迁移人数（行 = 上一年，列 = 主窗口）==")
tab = pd.crosstab(mig["上一年分层"], mig["主窗口分层"]).reindex(index=rows, columns=cols, fill_value=0)
print(tab.to_string(), "\n")

print("== 3. 迁移比例（每行加起来 100%）==")
print((tab.div(tab.sum(axis=1), axis=0) * 100).round(1).iloc[:-1].to_string(), "\n")

prev.reset_index().to_csv(ROOT / "data" / "rfm_prev.csv", index=False, encoding="utf-8-sig")
mig.reset_index().to_csv(ROOT / "data" / "segment_migration.csv", index=False, encoding="utf-8-sig")
print("已保存：data/rfm_prev.csv、data/segment_migration.csv")

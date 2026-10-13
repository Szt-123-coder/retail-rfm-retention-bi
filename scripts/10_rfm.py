"""第 5 步：计算主窗口的 RFM 并打分。口径见 docs/口径与决策.md。
先运行 08_clean.py，再在项目根目录运行：
    python scripts/10_rfm.py
输出：data/rfm_main.csv（每个客户一行）
"""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "clean_lines.csv"
OUT = ROOT / "data" / "rfm_main.csv"

START, END = pd.Timestamp("2010-12-10"), pd.Timestamp("2011-12-09")  # 主窗口（含两端）
CUTOFF = pd.Timestamp("2011-12-10")  # R = 截止日 − 最后一个有效购买日

use = ["Customer ID", "InvoiceDay", "Amount", "is_product", "has_customer", "is_valid_purchase_day"]
d = pd.read_csv(SRC, usecols=use, parse_dates=["InvoiceDay"])
w = d[(d["InvoiceDay"] >= START) & (d["InvoiceDay"] <= END) & d["has_customer"]]

# 有效购买日 → R、F
days = w[w["is_valid_purchase_day"]].drop_duplicates(["Customer ID", "InvoiceDay"])
rf = days.groupby("Customer ID")["InvoiceDay"].agg(last="max", F="size")
rf["R"] = (CUTOFF - rf["last"]).dt.days

# M = 窗口内商品行净金额（含取消冲减），只算窗口内有有效购买日的客户
m = w[w["is_product"]].groupby("Customer ID")["Amount"].sum().rename("M")
rfm = rf.join(m, how="left").fillna({"M": 0})

print(f"主窗口 {START:%Y-%m-%d} ~ {END:%Y-%m-%d}，有至少 1 个有效购买日的客户：{len(rfm):,}\n")

print("== 1. F（有效购买日数）分布 ==")
f_counts = rfm["F"].clip(upper=10).value_counts().sort_index()
f_counts.index = [str(i) if i < 10 else "≥10" for i in f_counts.index]
print(pd.DataFrame({"客户数": f_counts, "占比": (f_counts / len(rfm)).map("{:.1%}".format)}).to_string(), "\n")

print("== 2. R（天）和 M（£）的分位数 ==")
q = [0, 0.2, 0.4, 0.6, 0.8, 1]
print(pd.DataFrame({"R": rfm["R"].quantile(q), "M": rfm["M"].quantile(q).round(2)}, index=q).to_string())
print(f"M < 0 的客户：{(rfm['M'] < 0).sum():,}；M = 0 的客户：{(rfm['M'] == 0).sum():,}\n")

# ---------- 打分 ----------
rfm["R_score"] = pd.qcut(rfm["R"], 5, labels=[5, 4, 3, 2, 1]).astype(int)  # 越近越高
rfm["M_score"] = pd.qcut(rfm["M"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["F_score"] = pd.cut(rfm["F"], [0, 1, 2, 4, 9, float("inf")], labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M_negative"] = rfm["M"] < 0
rfm["high_value"] = rfm["M_score"] == 5
rfm["churned_by_rule"] = rfm["R"] >= 181  # 最后一个有效购买日 ≤ 2011-06-12


def segment(r, f):
    if r >= 4:
        return "核心活跃" if f >= 4 else ("成长中" if f >= 2 else "近期仅一个有效购买日")
    if r == 3:
        return "观望"
    return "高频待召回" if f >= 3 else "低频沉睡"


rfm["segment"] = [segment(r, f) for r, f in zip(rfm["R_score"], rfm["F_score"])]

print("== 3. 各项得分的人数 ==")
print(pd.DataFrame({s: rfm[f"{s}_score"].value_counts().sort_index() for s in "RFM"}).to_string(), "\n")

print("== 4. R 得分 × F 得分 人数交叉表（行 = R，列 = F）==")
print(pd.crosstab(rfm["R_score"], rfm["F_score"]).to_string(), "\n")

print("== 5. 分层人数，以及每层里高价值（M5）、按规则流失的人数 ==")
print(rfm.groupby("segment").agg(人数=("F", "size"), 高价值=("high_value", "sum"),
                                 按规则流失=("churned_by_rule", "sum"), M合计=("M", "sum"))
      .round(2).sort_values("人数", ascending=False).to_string(), "\n")

print("== 6. 随机 8 个客户 ==")
print(rfm.sample(8, random_state=1).to_string())

rfm.reset_index().to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\n已保存：{OUT}")

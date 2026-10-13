"""把 online_retail_II.xlsx 的两个工作表合并，存成一个 CSV，后面都读这个 CSV（快很多）。
只做格式转换，不做任何清洗；清洗规则等数据质量问题逐个确认后再写。
用法（在项目根目录运行）：python scripts/01_xlsx_to_csv.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "online+retail+ii" / "online_retail_II.xlsx"
DST = ROOT / "data" / "online_retail_II.csv"

# Invoice、StockCode 里有字母（如 C489449、85123A），按文本读，避免被当成数字
sheets = pd.read_excel(SRC, sheet_name=None, dtype={"Invoice": str, "StockCode": str})

frames = []
for name, df in sheets.items():
    df["Sheet"] = name  # 记下来源工作表，方便之后核对两表重叠的部分
    frames.append(df)
    print(f"{name}: {len(df):,} 行")

df = pd.concat(frames, ignore_index=True)
print(f"合并后：{len(df):,} 行（应为 1,067,371）")

df.to_csv(DST, index=False, encoding="utf-8-sig")  # utf-8-sig 让 Excel/Power BI 打开不乱码
print(f"已保存：{DST}")

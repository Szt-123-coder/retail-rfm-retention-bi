# Power BI 搭建步骤（3 页）

数据：先依次运行 `08_clean.py → 10_rfm.py → 11_migration.py → 12_cohort.py → 13_powerbi_tables.py → 17_action_list.py`，表都在 `data/powerbi/`。口径见 `docs/口径与决策.md`。

## 1. 导入数据

主页 → 获取数据 → 文本/CSV，依次导入 5 张表，文件原始格式选 **65001: Unicode (UTF-8)**，然后点「转换数据」检查类型：

| 表 | 一行是什么 | 检查类型 |
|---|---|---|
| customers | 主窗口有有效购买日的一个客户（4,260 行） | Customer ID 整数；last_valid_day、first_valid_day 日期；M 小数；high_value、churned_by_rule、M_negative 为 True/False |
| migration | 两个窗口出现过的一个客户 | Customer ID 整数 |
| cohort | 一个首单月 × 第 k 月 | k、active、size 整数；rate 小数 |
| repurchase | 一个预热期 × N | N、分母、分子 整数 |
| actions | 行动名单里的一个客户（258 行） | 行动顺序、行动内序号、Customer ID、R 整数；最后有效购买日 日期；金额小数 |

关系：只保留 customers[Customer ID] ↔ migration[Customer ID]（双向），让第 2 页的高价值切片器能筛迁移矩阵；其余表各自独立，actions 不和任何表建关系（Power BI 自动检测出的关系要删掉）。

排序：customers[segment] 按 segment_order 排序；actions[行动] 按 行动顺序 排序；migration 的显示列按对应的排序列排序（见第 4 节）。

计算列：

```DAX
高价值标签 = IF ( customers[high_value], "高价值", "非高价值" )   // customers 表；切片器用文本列，避免空白被当成 FALSE
```

## 2. 度量值（新建度量值，粘贴）

```DAX
客户数 = COUNTROWS ( customers )

一次性客户占比 =
DIVIDE ( CALCULATE ( COUNTROWS ( customers ), customers[F] = 1 ), [客户数] )

按规则流失人数 =
CALCULATE ( COUNTROWS ( customers ), customers[churned_by_rule] = TRUE () )

90天回购率 =
CALCULATE (
    DIVIDE ( SUM ( repurchase[分子] ), SUM ( repurchase[分母] ) ),
    repurchase[N] = 90,
    repurchase[预热期（月）] = 1
)

回购率 = DIVIDE ( SUM ( repurchase[分子] ), SUM ( repurchase[分母] ) )

M合计 = SUM ( customers[M] )

M占比 = DIVIDE ( [M合计], CALCULATE ( [M合计], ALL ( customers[segment], customers[segment_order] ) ) )

留存率 = DIVIDE ( SUM ( cohort[active] ), SUM ( cohort[size] ) )

迁移人数 = COUNTROWS ( migration )

迁移占比 =
DIVIDE (
    [迁移人数],
    CALCULATE ( [迁移人数], ALLSELECTED ( migration[主窗口分层_显示], migration[主窗口分层排序] ) )
)

行动人数 = COUNTROWS ( actions )
```

百分比类度量值：选中 → 度量工具 → 格式设为百分比，1 位小数。

## 3. 第 1 页「留存总览」

- 4 张卡片：客户数、一次性客户占比、90天回购率、按规则流失人数。
- 矩阵（cohort 热力图）：行 = cohort_label，列 = k，值 = 留存率；筛选器把 k 限制在 1～12；值 → 条件格式 → 背景色（渐变）。
- 簇状柱形图：X 轴 = N，Y 轴 = 回购率，图例 = 预热期（月）。主口径是预热期 1；另外两组是敏感性分析。
- 文本框写口径：数据截至 2011-12-09；矩阵不含不完整的 2011-12；2009-12 行为"期初已观察客户（既往历史未知）"。

## 4. 第 2 页「RFM 分层」

- 条形图：Y 轴 = segment，X 轴 = 客户数；再放一个同样的条形图，X 轴 = M占比。
- 矩阵（R×F）：行 = R_score，列 = F_score，值 = 客户数。
- 矩阵（迁移）：行 = migration[上一年分层_显示]，列 = migration[主窗口分层_显示]，值 = 迁移占比（每格 ÷ 该行合计，1 位小数）。两个显示列分别按 上一年分层排序、主窗口分层排序 排序（排序列另建，不能由显示列算出，否则循环依赖）。
- 切片器：customers[高价值标签]。

## 5. 第 3 页「行动名单」

- 表格（actions 表）：行动内序号、Customer ID、分层依据、分层、高价值、按规则流失、最后有效购买日、R、主窗口M、上一年M、取消金额、取消占比；不汇总，按行动内序号升序。金额 2 位小数，取消占比 0.0%。
- 切片器：行动，单选，默认电话召回。
- 卡片：行动人数。四组应为 电话召回 68、取消回访 21、邮件召回 167、内部核实 2。
- 文本框：按规则流失 = 最后一个有效购买日距 2011-12-09 满 180 天，不代表客户不会再来。
- 空白与 0：上一年M 空白 = 上一年没有有效购买日；取消金额 0.00 = 主窗口算过、没有取消；按上一年分层挑出的行（主窗口没有有效购买日）高价值、按规则流失、取消两列都是空白，表示没有统计。

## 6. 核对

搭好后对照 `13_powerbi_tables.py` 打印的核对数：一次性客户占比、按规则流失人数、高频待召回且高价值人数，三者应与卡片和筛选结果一致；90天回购率应为 40.9%。第 3 页四组人数对照 `17_action_list.py` 打印的 68 / 21 / 167 / 2。

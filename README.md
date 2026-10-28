# 学生成绩分析工具（Grade Analyzer）

读取 CSV 成绩表，一键完成统计分析 + 图表生成 + 文本报告输出。
纯 Python 标准库 + matplotlib，无其他依赖。

## 功能

| 功能 | 说明 |
|---|---|
| 成绩读取 | 从 CSV 读取任意科目的成绩表（自动识别列） |
| 学生统计 | 每人总分、平均分、班级排名 |
| 科目统计 | 各科平均分 / 最高分 / 最低分 / 及格率 / 最高分学生 |
| 班级对比 | 按班级汇总各科平均分 |
| 图表生成 | 各科平均分柱状图 + 各班各科分组柱状图 |
| 文本报告 | 输出 5 个板块的分析报告 `分析报告.txt` |

## 快速开始

```bash
# 1. 安装依赖（只需要 matplotlib）
pip install matplotlib

# 2. 用自带的示例数据跑一遍
python main.py

# 3. 用你自己的成绩表
python main.py -f 我的成绩.csv
```

运行后生成 3 个文件：

```
科目平均分对比.png
班级各科平均分对比.png
分析报告.txt
```

## CSV 数据格式

第一行为表头，必须包含 `学号`、`姓名`、`班级`，其余列自动识别为科目：

```csv
学号,姓名,班级,语文,数学,英语,Python程序设计
20230101,林晓薇,软件工程1班,88,92,79,99
20230102,陈思远,软件工程1班,85,90,82,93
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `-f / --file` | 成绩 CSV 文件路径 | `grades.csv` |
| `-o / --output` | 报告输出目录 | 当前目录 |
| `--no-chart` | 不生成图表，只要文本报告 | 关闭 |

## 代码结构

```
main.py
├── load_data()            # 读取 CSV
├── calc_student_stats()   # 每人总分/平均分/排名
├── calc_subject_stats()   # 每科统计
├── calc_class_stats()     # 班级汇总
├── make_chart()           # 科目平均分柱状图
├── make_class_chart()     # 班级分组柱状图
├── build_report()         # 生成文本报告
└── main()                 # argparse 入口
```

## 设计亮点

- **中文图表**：自动探测 Windows / Mac / Linux 的中文字体文件并注册给 matplotlib，跨平台不出现方块
- **无图形界面也能跑**：`matplotlib.use("Agg")`，服务器 / CI 环境直接出图
- **Excel 友好**：CSV 输出用 `utf-8-sig` 编码，Excel 打开不乱码
- **命令行工具**：argparse 支持自定义输入输出，符合 Unix 工具习惯

"""
学生成绩分析工具 (Grade Analyzer)
------------------------------------
读取 CSV 成绩表，完成统计分析并生成图表与文本报告。

功能：
  1. 读取 CSV 成绩数据（学号 / 姓名 / 班级 / 各科成绩）
  2. 计算每人总分、平均分，生成班级排名
  3. 统计各科平均分、最高分、最低分、及格率
  4. 按班级汇总对比
  5. 生成各科平均分对比图（保存为 png）
  6. 输出格式化文本报告

用法：
  python main.py                      # 分析默认的 grades.csv
  python main.py -f 我的成绩.csv       # 分析指定文件
  python main.py --chart-only         # 只生成图表
"""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

# 让 matplotlib 在没有图形界面的环境也能跑（非常重要，否则 Windows 上会卡）
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 中文字体设置：优先用系统里真实存在的字体文件，跨平台都能跑
from matplotlib import font_manager

_FONT_FILE_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",                                  # Windows 微软雅黑
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",      # Linux Noto
    "/System/Library/Fonts/PingFang.ttc",                          # Mac 苹方
]

font_found = False
for font_path in _FONT_FILE_CANDIDATES:
    if Path(font_path).exists():
        # 把字体文件注册进 matplotlib，再设为默认字体
        font_manager.fontManager.addfont(font_path)
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        plt.rcParams["font.sans-serif"] = [font_name]
        font_found = True
        break

if not font_found:
    # 兜底：按字体名找
    for font_name in ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei"]:
        try:
            font_manager.findfont(font_name, fallback_to_default=False)
            plt.rcParams["font.sans-serif"] = [font_name]
            break
        except Exception:
            continue

plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示为方块


# ============ 第一部分：读取数据 ============
def load_data(file_path):
    """
    从 CSV 文件读取成绩数据。

    返回 (subjects, students)：
      subjects: 科目名称列表，比如 ["语文", "数学", ...]
      students: 学生字典列表，每个字典包含学号、姓名、班级和各科成绩

    为什么要用字典列表？因为每一行数据有多个"字段"，
    字典能让代码读起来是 student["数学"] 而不是 student[3]，不容易搞错。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到文件：{file_path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            raise ValueError("CSV 文件是空的")

        # 表头里前 3 列是固定字段，剩下都是科目
        fixed_cols = ["学号", "姓名", "班级"]
        subjects = [col for col in reader.fieldnames if col not in fixed_cols]

        if not subjects:
            raise ValueError("没有识别到任何科目列，请检查 CSV 表头")

        students = []
        for row in rows:
            student = {
                "学号": row["学号"],
                "姓名": row["姓名"],
                "班级": row["班级"],
                "成绩": {},
            }
            for subj in subjects:
                # 把字符串转成数字；空值或异常值当作 None
                try:
                    student["成绩"][subj] = float(row[subj])
                except (ValueError, KeyError):
                    student["成绩"][subj] = None
            students.append(student)

    return subjects, students


# ============ 第二部分：计算统计量 ============
def calc_student_stats(students, subjects):
    """
    为每个学生计算总分和平均分，并生成班级排名。

    关键点：排名是"每个班内各自排"，不是全校混排。
    做法：先按班级分组，组内按总分降序排，再给名次。
    """
    for student in students:
        scores = [s for s in student["成绩"].values() if s is not None]
        student["总分"] = sum(scores)
        student["平均分"] = round(sum(scores) / len(scores), 1) if scores else 0.0

    # 按班级分组
    classes = {}
    for student in students:
        classes.setdefault(student["班级"], []).append(student)

    # 每个班内部排名
    for class_name, members in classes.items():
        members.sort(key=lambda s: s["总分"], reverse=True)
        for rank, student in enumerate(members, start=1):
            student["班级排名"] = rank

    return students


def calc_subject_stats(students, subjects):
    """
    统计每个科目的平均分、最高分、最低分、及格率。
    返回一个字典：{科目: {avg, max, min, pass_rate, max_student, min_student}}
    """
    stats = {}
    for subj in subjects:
        pairs = [
            (s["成绩"][subj], s["姓名"])
            for s in students
            if s["成绩"][subj] is not None
        ]
        if not pairs:
            continue

        scores = [p[0] for p in pairs]
        best = max(pairs, key=lambda p: p[0])
        worst = min(pairs, key=lambda p: p[0])
        pass_count = sum(1 for sc in scores if sc >= 60)

        stats[subj] = {
            "avg": round(sum(scores) / len(scores), 1),
            "max": best[0],
            "max_student": best[1],
            "min": worst[0],
            "min_student": worst[1],
            "pass_rate": round(pass_count / len(scores) * 100, 1),
        }
    return stats


def calc_class_stats(students, subjects):
    """
    按班级汇总：班级平均总分、各科平均分。
    """
    classes = {}
    for student in students:
        classes.setdefault(student["班级"], []).append(student)

    result = {}
    for class_name, members in classes.items():
        total_avg = round(sum(m["总分"] for m in members) / len(members), 1)
        subject_avg = {}
        for subj in subjects:
            vals = [m["成绩"][subj] for m in members if m["成绩"][subj] is not None]
            subject_avg[subj] = round(sum(vals) / len(vals), 1) if vals else 0.0
        result[class_name] = {
            "人数": len(members),
            "总分平均": total_avg,
            "各科平均": subject_avg,
        }
    return result


# ============ 第三部分：生成图表 ============
def make_chart(subject_stats, output_path="科目平均分对比.png"):
    """
    画柱状图：各科平均分对比。
    每个柱子顶上标注具体数值，方便一眼看出差距。
    """
    subjects = list(subject_stats.keys())
    averages = [subject_stats[s]["avg"] for s in subjects]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(subjects, averages, color="#4A7EBB", width=0.55)

    # 在柱子上标数值
    for bar, value in zip(bars, averages):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.8,
            f"{value}",
            ha="center",
            va="bottom",
            fontsize=11,
        )

    ax.set_title("各科平均分对比", fontsize=15, pad=15)
    ax.set_ylabel("平均分", fontsize=12)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)  # 网格线在柱子下面，不遮挡

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path


def make_class_chart(class_stats, subjects, output_path="班级各科平均分对比.png"):
    """
    画分组柱状图：每个班级各科平均分。
    """
    class_names = list(class_stats.keys())
    n_classes = len(class_names)
    n_subjects = len(subjects)
    bar_width = 0.8 / n_subjects
    x = range(n_subjects)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#4A7EBB", "#E8955C", "#6BAF72", "#B57DB5"]

    for i, class_name in enumerate(class_names):
        values = [class_stats[class_name]["各科平均"][s] for s in subjects]
        offset = (i - (n_classes - 1) / 2) * bar_width
        positions = [p + offset for p in x]
        ax.bar(positions, values, width=bar_width, label=class_name,
               color=colors[i % len(colors)])

    ax.set_xticks(list(x))
    ax.set_xticklabels(subjects)
    ax.set_ylabel("平均分")
    ax.set_title("各班级各科平均分对比", fontsize=15, pad=15)
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    return output_path


# ============ 第四部分：生成文本报告 ============
def build_report(students, subjects, subject_stats, class_stats):
    """把统计结果拼成一份可读的文本报告。"""
    lines = []
    line = "=" * 60

    lines.append(line)
    lines.append("学生成绩分析报告".center(50))
    lines.append(line)
    lines.append(f"学生总数：{len(students)} 人    科目数：{len(subjects)} 门")
    lines.append(f"班级数：{len(class_stats)} 个")
    lines.append("")

    # 各科统计
    lines.append("【一、各科成绩概况】")
    lines.append("-" * 60)
    lines.append(f"{'科目':<10}{'平均分':>8}{'最高分':>8}{'最低分':>8}{'及格率':>9}")
    for subj, st in subject_stats.items():
        lines.append(
            f"{subj:<10}{st['avg']:>8}{st['max']:>8.0f}{st['min']:>8.0f}{st['pass_rate']:>8}%"
        )
    lines.append("")

    # 单科最高分获得者
    lines.append("【二、各科最高分】")
    lines.append("-" * 60)
    for subj, st in subject_stats.items():
        lines.append(f"{subj}：{st['max_student']}（{st['max']:.0f} 分）")
    lines.append("")

    # 班级对比
    lines.append("【三、班级对比】")
    lines.append("-" * 60)
    header = f"{'班级':<14}{'人数':>5}{'总分平均':>10}"
    for subj in subjects:
        header += f"{subj:>8}"
    lines.append(header)
    for class_name, cs in class_stats.items():
        row = f"{class_name:<14}{cs['人数']:>5}{cs['总分平均']:>10}"
        for subj in subjects:
            row += f"{cs['各科平均'][subj]:>8}"
        lines.append(row)
    lines.append("")

    # 总分排行
    lines.append("【四、总分排行（各班前三名）】")
    lines.append("-" * 60)
    by_class = {}
    for student in students:
        by_class.setdefault(student["班级"], []).append(student)
    for class_name, members in by_class.items():
        members.sort(key=lambda s: s["总分"], reverse=True)
        lines.append(f"▍{class_name}")
        for student in members[:3]:
            lines.append(
                f"  第{student['班级排名']}名  {student['姓名']}  "
                f"总分 {student['总分']:.0f}  平均 {student['平均分']}"
            )
    lines.append("")

    # 需要关注的学生（有不及格科目）
    lines.append("【五、需要关注的学生（存在不及格科目）】")
    lines.append("-" * 60)
    found = False
    for student in students:
        failed = [s for s, v in student["成绩"].items() if v is not None and v < 60]
        if failed:
            found = True
            lines.append(f"{student['姓名']}（{student['班级']}）：{'、'.join(failed)} 不及格")
    if not found:
        lines.append("无（全部及格）")
    lines.append("")

    lines.append(line)
    return "\n".join(lines)


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(description="学生成绩分析工具")
    parser.add_argument("-f", "--file", default="grades.csv", help="CSV 成绩文件路径")
    parser.add_argument("-o", "--output", default="分析报告.txt", help="报告输出文件名")
    parser.add_argument("--no-chart", action="store_true", help="不生成图表")
    args = parser.parse_args()

    try:
        subjects, students = load_data(args.file)
    except (FileNotFoundError, ValueError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)

    students = calc_student_stats(students, subjects)
    subject_stats = calc_subject_stats(students, subjects)
    class_stats = calc_class_stats(students, subjects)

    report = build_report(students, subjects, subject_stats, class_stats)
    Path(args.output).write_text(report, encoding="utf-8")
    print(report)
    print(f"\n报告已保存：{args.output}")

    if not args.no_chart:
        chart1 = make_chart(subject_stats)
        chart2 = make_class_chart(class_stats, subjects)
        print(f"图表已生成：{chart1}、{chart2}")


if __name__ == "__main__":
    main()

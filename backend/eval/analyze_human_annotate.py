# -*- coding: utf-8 -*-
"""
M2-5 人工校准汇总:读取用户已填的标注文件,计算 judge vs 人工一致率。

用法:
    .venv\\Scripts\\python.exe eval/analyze_human_annotate.py [YYYY-MM-DD]
(默认读取 reports/ 下最新一份 -human-annotate.md)
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402

# | judge - human | <= THRESHOLD 视为一致
AGREE_THRESHOLD = 0.3


def parse_table(text: str):
    # 只解析「## 打分表」到「## 完整答案」之间的表格,避免误读完整答案段内的 markdown 表格
    start = text.find("## 打分表")
    end = text.find("## 完整答案")
    if start == -1:
        return []
    segment = text[start:end] if end > start else text[start:]
    rows = []
    for line in segment.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 7 or cells[0] == "id":
            continue
        # 跳过 markdown 表格分隔行(| ---- | ... |)
        if all(not c or set(c) == {"-"} for c in cells):
            continue
        rows.append(cells)
    return rows


def to_float(s):
    s = s.strip()
    if not s or s in ("—", "-", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main() -> int:
    report_dir = settings.EVAL_REPORT_DIR
    files = sorted(glob.glob(os.path.join(report_dir, "*-human-annotate.md")))
    if not files:
        print("[失败] 没有找到标注文件,请先运行 export_human_annotate.py")
        return 1

    date = sys.argv[1] if len(sys.argv) > 1 else None
    if date:
        target = os.path.join(report_dir, f"{date}-human-annotate.md")
        if not os.path.exists(target):
            print(f"[失败] 找不到 {target}")
            return 1
        files = [target]
    else:
        files = [files[-1]]

    path = files[0]
    with open(path, encoding="utf-8") as f:
        text = f.read()

    rows = parse_table(text)
    if not rows:
        print("[失败] 标注文件里没有数据行,或 human_faith/human_rel 尚未填写")
        return 1

    faith_agree, faith_total = 0, 0
    rel_agree, rel_total = 0, 0
    filled = 0
    for cells in rows:
        judge_f = to_float(cells[3])
        judge_r = to_float(cells[4])
        human_f = to_float(cells[5])
        human_r = to_float(cells[6])
        if human_f is not None and judge_f is not None:
            faith_total += 1
            if abs(judge_f - human_f) <= AGREE_THRESHOLD:
                faith_agree += 1
            filled += 1
        if human_r is not None and judge_r is not None:
            rel_total += 1
            if abs(judge_r - human_r) <= AGREE_THRESHOLD:
                rel_agree += 1

    print(f"标注文件: {os.path.basename(path)}")
    print(f"已填条数: {filled}/{len(rows)}")
    if faith_total:
        print(f"faithfulness 一致率: {faith_agree}/{faith_total} = {faith_agree / faith_total:.2%}")
    if rel_total:
        print(f"answer_relevancy 一致率: {rel_agree}/{rel_total} = {rel_agree / rel_total:.2%}")
    if filled < len(rows):
        print(f"[提示] 还有 {len(rows) - filled} 条未填写 human 打分")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

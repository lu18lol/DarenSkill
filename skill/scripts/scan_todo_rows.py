#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
扫描飞书"+csv-get"导出的身份列/评审列文本，找出「身份列有人但评审列任一为空」的待审行。

用法（在 execute_code 或终端里）:
    1. 先分别窄读两段并落盘，避开被污染单元格的跨列污染:
         lark sheets +csv-get --spreadsheet-token T --sheet-id SID --range A1:L270 --format json
         lark sheets +csv-get --spreadsheet-token T --sheet-id SID --range A271:L521 --format json
         (身份列区间, 存 idcols.json: {"<range>": annotated_csv})
       # 两段必须分开读；整表一次读会被带引号的链接单元格污染。

    2. 再窄读评审列区间两段, 存 revcols.json (格式同上):
         --range M1:P270 / M271:P521      # 列字母以当次表头为准, 不要硬编码

    3. python scan_todo_rows.py idcols.json revcols.json
       → 输出待审行清单 (row, 昵称, 抖音号, 主页链接, 商务, 提报日期)

⚠️ 本脚本的输出只是"筛子"——命中行必须再对每行单独窄读 `N{r}:P{r}` 复核,
   因为链接列未闭合引号会让已写好的行在整段解析里显示为全空（row124 类误报）。
   只有窄读也为空的才是真漏行。详见 SKILL.md「错位/误报」小节。
"""
import json, re, sys


def parse_annotated(txt):
    """annotated_csv -> {row_no: raw_body}"""
    out = {}
    for line in (txt or "").split("\n"):
        m = re.match(r"\[row=(\d+)\] (.*)$", line)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def split_csv_line(s):
    """最小 CSV 行解析：识别双引号包裹字段与 '' 转义。"""
    parts, cur, inq, i = [], "", False, 0
    while i < len(s):
        c = s[i]
        if c == '"':
            if inq:
                if i + 1 < len(s) and s[i + 1] == '"':
                    cur += '"'; i += 2; continue
                inq = False; i += 1; continue
            else:
                inq = True; i += 1; continue
        if c == ',' and not inq:
            parts.append(cur); cur = ""; i += 1; continue
        cur += c; i += 1
    parts.append(cur)
    return parts


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    rows = {}
    for _rng, txt in d.items():
        rows.update(parse_annotated(txt))
    return rows


def main(idcols_path, revcols_path):
    idr = load(idcols_path)
    rvr = load(revcols_path)

    todo = []
    for n in sorted(idr):
        if n <= 2:            # 第1行是表头说明, 第2行是列名行
            continue
        ip = split_csv_line(idr[n])
        # A产品 B提报日期 C达人昵称 D抖音号 E主页链接 F商务
        prod = ip[0].strip() if len(ip) > 0 else ""
        date = ip[1].strip() if len(ip) > 1 else ""
        nick = ip[2].strip() if len(ip) > 2 else ""
        dyid = ip[3].strip() if len(ip) > 3 else ""
        link = ip[4].strip() if len(ip) > 4 else ""
        biz  = ip[5].strip() if len(ip) > 5 else ""

        rp = split_csv_line(rvr.get(n, ""))
        # M达人反馈 N标签 O评估 P是否合适  (列字母以当次表头为准)
        tag = rp[1].strip() if len(rp) > 1 else ""
        ev  = rp[2].strip() if len(rp) > 2 else ""
        vd  = rp[3].strip() if len(rp) > 3 else ""

        if (nick or link) and not (tag and ev and vd):
            todo.append({
                "row": n, "nickname": nick, "douyin_id": dyid,
                "link": link, "biz": biz, "date": date, "product": prod,
            })

    print("疑似待审行: %d" % len(todo))
    print("=" * 60)
    for t in todo:
        print("row%d | %s | 抖音号 %s | 商务 %s | %s | %s" %
              (t["row"], t["nickname"], t["douyin_id"], t["biz"], t["date"], t["link"][:50]))
    print("=" * 60)
    print("⚠️ 逐行窄读 N{row}:P{row} 复核后再下结论——整段比对会有链接列引号造成的误报。")
    return todo


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    main(sys.argv[1], sys.argv[2])

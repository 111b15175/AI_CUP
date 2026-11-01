# -*- coding: utf-8 -*-
"""提交檔工具（隨參賽者資料一起發布，檔名為 make_submission.py）。

兩個用途：

  1. 產生空白範本 —— 涵蓋全部測試影像，每張先填空陣列，你再把預測寫進去
         python make_submission.py --template my_submission.json

  2. 檢查格式 —— 送出前先自我檢查，避免因格式問題被退件
         python make_submission.py --check my_submission.json

檢查項目與主辦方評測程式的格式驗證完全一致。通過不代表分數高，
只代表格式正確、可以被正常評分。

提交檔格式
----------
以測試影像路徑為 key，值為該影像的預測物件陣列：

{
  "test/EO/image/test_001.jpg": [
    {"label": "solar_panel", "points": [[120.5, 88.0], [340.2, 85.1], [345.0, 300.7], [118.9, 305.2]]},
    {"label": "crack", "points": [[210.0, 150.0], [260.0, 152.0], [258.0, 205.0], [208.0, 203.0]],
     "reason": "模組表面可見明顯裂紋，推測為外力撞擊所致。"}
  ],
  "test/EO/image/test_002.jpg": []
}

  key       須與 test_images.csv 中的字串完全一致；未列出的影像視為無偵測結果
  label     solar_panel / hotspot / crack
  points    3~100 個 [x, y]，像素座標，原點在左上角（送 2 點會視為對角矩形展開）
  reason    hotspot 與 crack 必填；solar_panel 會被忽略；留空該筆記 0 分

沒有 confidence 欄位 —— 所有送出的框都計入 Precision 分母，濫送低信心框會拉低分數。
"""
import argparse
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

CLASSES = ("solar_panel", "hotspot", "crack")
ANOMALY = ("hotspot", "crack")
MAX_BYTES = 50 * 1024 * 1024
MAX_OBJECTS_PER_IMAGE = 500
MAX_TOTAL_OBJECTS = 400_000
MAX_VERTICES = 100
MIN_VERTICES = 2
MAX_REASON_CHARS = 500
COORD_ABS_LIMIT = 1e6


def load_test_list(path):
    if not os.path.exists(path):
        sys.exit("找不到 {}（請在解壓後的資料集根目錄執行）".format(path))
    with open(path, encoding="utf-8") as f:
        return [r["filename"] for r in csv.DictReader(f)]


def make_template(test_ids, out):
    with open(out, "w", encoding="utf-8") as f:
        f.write("{\n")
        for i, k in enumerate(test_ids):
            tail = "," if i < len(test_ids) - 1 else ""
            f.write('  {}: []{}\n'.format(json.dumps(k, ensure_ascii=False), tail))
        f.write("}\n")
    print("已產生範本：{}（{} 張測試影像，每張先填空陣列）".format(out, len(test_ids)))
    print("把預測填進對應的陣列後，用 --check 檢查格式。")


def check(path, test_ids):
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        return ["檔案 {:.1f} MB 超過上限 {} MB".format(size / 1e6, MAX_BYTES // 1024 // 1024)]

    def reject(name):
        raise ValueError("不接受 NaN / Infinity（出現 {}）".format(name))

    try:
        with open(path, encoding="utf-8") as f:
            data = json.loads(f.read(), parse_constant=reject)
    except ValueError as e:
        return ["JSON 解析失敗：{}".format(e)]

    errs = []
    if not isinstance(data, dict):
        return ["最外層必須是物件（以影像路徑為 key），實得 {}".format(type(data).__name__)]

    valid = set(test_ids)
    unknown = [k for k in data if k not in valid]
    if unknown:
        errs.append("有 {} 個 key 不在 test_images.csv 中，例如 {}".format(len(unknown), unknown[:3]))

    total = 0
    for key, objs in data.items():
        where = "'{}'".format(key)
        if not isinstance(objs, list):
            errs.append("{} 的值必須是陣列".format(where))
            continue
        if len(objs) > MAX_OBJECTS_PER_IMAGE:
            errs.append("{} 有 {} 個物件，超過上限 {}".format(where, len(objs), MAX_OBJECTS_PER_IMAGE))
        total += len(objs)
        for j, o in enumerate(objs):
            at = "{} 第 {} 個物件".format(where, j + 1)
            if not isinstance(o, dict):
                errs.append("{} 必須是物件".format(at))
                continue
            if o.get("label") not in CLASSES:
                errs.append("{} 的 label 是 {!r}，必須是 {}".format(at, o.get("label"), "/".join(CLASSES)))
            pts = o.get("points")
            if not isinstance(pts, list) or not (MIN_VERTICES <= len(pts) <= MAX_VERTICES):
                errs.append("{} 的 points 必須是 {}~{} 個座標".format(at, MIN_VERTICES, MAX_VERTICES))
            else:
                for p in pts:
                    if not isinstance(p, (list, tuple)) or len(p) != 2:
                        errs.append("{} 的每個座標必須是 [x, y]".format(at))
                        break
                    x, y = p
                    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (x, y)):
                        errs.append("{} 的座標必須是數值".format(at))
                        break
                    if not (math.isfinite(x) and math.isfinite(y)):
                        errs.append("{} 的座標不可為 NaN / Infinity".format(at))
                        break
                    if abs(x) > COORD_ABS_LIMIT or abs(y) > COORD_ABS_LIMIT:
                        errs.append("{} 的座標超出合理範圍".format(at))
                        break
            if o.get("label") in ANOMALY:
                r = o.get("reason")
                if r is not None and not isinstance(r, str):
                    errs.append("{} 的 reason 必須是字串".format(at))
                elif isinstance(r, str) and len(r) > MAX_REASON_CHARS:
                    errs.append("{} 的 reason 超過 {} 字".format(at, MAX_REASON_CHARS))
        if len(errs) > 40:
            errs.append("（錯誤過多，僅顯示前 40 筆）")
            break
    if total > MAX_TOTAL_OBJECTS:
        errs.append("總物件數 {} 超過上限 {}".format(total, MAX_TOTAL_OBJECTS))

    if not errs:
        n_an = sum(1 for objs in data.values() for o in objs if o.get("label") in ANOMALY)
        blank = sum(1 for objs in data.values() for o in objs
                    if o.get("label") in ANOMALY
                    and not (isinstance(o.get("reason"), str) and o["reason"].strip()))
        missing = len(valid) - len(data)
        print("格式正確 ✓")
        print("  檔案大小    {:.2f} MB".format(size / 1e6))
        print("  影像        {} / {}".format(len(data), len(valid)))
        print("  物件        {}（其中異常 {}）".format(total, n_an))
        if missing > 0:
            print("  提醒：有 {} 張測試影像未列出，將視為沒有偵測結果".format(missing))
        if blank > 0:
            print("  提醒：有 {} 個異常物件的 reason 為空，該筆文字分數會是 0".format(blank))
    return errs


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--template", metavar="OUT", help="產生涵蓋全部測試影像的空白範本")
    g.add_argument("--check", metavar="FILE", help="檢查提交檔格式")
    ap.add_argument("--test-images", default="test_images.csv")
    args = ap.parse_args()

    tl = args.test_images if os.path.isabs(args.test_images) else os.path.join(HERE, args.test_images)
    test_ids = load_test_list(tl)

    if args.template:
        make_template(test_ids, args.template)
        return
    if not os.path.exists(args.check):
        sys.exit("找不到 {}".format(args.check))
    errs = check(args.check, test_ids)
    if errs:
        print("格式有問題，共 {} 項：".format(len(errs)))
        for e in errs:
            print("  - {}".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

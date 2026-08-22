#!/usr/bin/env python3
"""과거 주간 베스트셀러를 거슬러 올라가며 수집한다 (히스토리 백필).

사용법:
  ALADIN_TTB_KEY=발급키 python3 scripts/backfill.py --weeks 26   # 최근 26주치
알라딘이 과거 몇 년까지 주는지는 실측으로 확인 — 빈 응답이 연속되면 멈춘다.
"""
import argparse
import datetime
import os
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def month_weeks_backwards(start: datetime.date):
    """(year, month, week_of_month)를 현재부터 과거로 무한히 낸다."""
    y, m = start.year, start.month
    w = (start.day - 1) // 7 + 1
    while True:
        yield y, m, w
        w -= 1
        if w < 1:
            m -= 1
            if m < 1:
                y, m = y - 1, 12
            last_day = (datetime.date(y + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1)).day
            w = (last_day - 1) // 7 + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=12)
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT / "scripts"))
    from fetch_rankings import load_dotenv
    load_dotenv()
    if not os.environ.get("ALADIN_TTB_KEY"):
        sys.exit("환경변수 ALADIN_TTB_KEY가 필요합니다.")

    gen = month_weeks_backwards(datetime.date.today())
    next(gen)  # 현재 주간은 fetch_rankings.py 기본 실행으로
    fails = 0
    for i, (y, m, w) in zip(range(args.weeks), gen):
        print(f"[{i+1}/{args.weeks}] {y}-{m:02d} {w}주차")
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "fetch_rankings.py"),
             "--year", str(y), "--month", str(m), "--week", str(w)],
            env=os.environ,
        )
        if r.returncode != 0:
            fails += 1
            if fails >= 3:
                print("연속 실패 3회 — 여기까지가 제공 범위로 보입니다.")
                break
        else:
            fails = 0


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""알라딘 오픈API에서 기독교 분과별 베스트셀러를 수집해 주간 스냅샷(JSON)으로 저장한다.

사용법:
  ALADIN_TTB_KEY=발급키 python3 scripts/fetch_rankings.py                       # 현재 주간
  ALADIN_TTB_KEY=발급키 python3 scripts/fetch_rankings.py --year 2025 --month 3 --week 2   # 과거 주간

수집 후 site/data.json 재생성까지 자동으로 이어진다.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://www.aladin.co.kr/ttb/api/ItemList.aspx"
KST = datetime.timezone(datetime.timedelta(hours=9))


def week_of_month(day: int) -> int:
    return (day - 1) // 7 + 1


def load_dotenv():
    """프로젝트 루트의 .env(깃 제외)에서 환경변수를 읽는다."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def fetch_section(ttb_key: str, cid: int, year=None, month=None, week=None, max_results=50):
    params = {
        "ttbkey": ttb_key,
        "QueryType": "Bestseller",
        "SearchTarget": "Book",
        "CategoryId": cid,
        "MaxResults": max_results,
        "start": 1,
        "output": "js",
        "Version": "20131101",
        "Cover": "Big",
    }
    if year:
        params.update({"Year": year, "Month": month, "Week": week})
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        text = res.read().decode("utf-8", errors="replace").strip().rstrip(";")
    payload = json.loads(text, strict=False)
    if "errorMessage" in payload:
        raise RuntimeError(f"알라딘 API 오류 (CID {cid}): {payload.get('errorMessage')}")
    books = []
    for it in payload.get("item", []):
        cover = it.get("cover", "") or ""
        books.append({
            "id": str(it.get("isbn13") or it.get("isbn") or it.get("itemId")),
            "title": it.get("title", ""),
            "author": it.get("author", ""),
            "publisher": it.get("publisher", ""),
            "pubDate": it.get("pubDate", ""),
            "cover": cover,
            "coverLarge": cover.replace("cover200", "cover500") if "cover200" in cover else cover,
            "link": it.get("link", ""),
            "salesPoint": it.get("salesPoint"),
            "bestRank": it.get("bestRank"),
            "description": it.get("description", ""),
            "categoryName": it.get("categoryName", ""),
        })
    return books


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--month", type=int)
    ap.add_argument("--week", type=int, help="월 기준 주차 (1~5)")
    args = ap.parse_args()

    load_dotenv()
    ttb_key = os.environ.get("ALADIN_TTB_KEY")
    if not ttb_key:
        sys.exit("환경변수 ALADIN_TTB_KEY가 필요합니다. (알라딘 오픈API에서 발급, .env 파일도 가능)")

    if args.year and not (args.month and args.week):
        sys.exit("--year를 쓰면 --month --week도 함께 지정해야 합니다.")

    if args.year:
        key = f"{args.year}-{args.month:02d}-w{args.week}"
    else:
        now = datetime.datetime.now(KST)
        key = f"{now.year}-{now.month:02d}-w{week_of_month(now.day)}"

    config = json.loads((ROOT / "data" / "categories.json").read_text(encoding="utf-8"))
    snapshot = {
        "week": key,
        "fetched_at": datetime.datetime.now(KST).isoformat(timespec="seconds"),
        "sample": False,
        "categories": {},
    }
    for sec in config["sections"]:
        y, m, w = (args.year, args.month, args.week) if args.year else (None, None, None)
        snapshot["categories"][sec["key"]] = fetch_section(ttb_key, sec["cid"], y, m, w)
        print(f"  {sec['label']}: {len(snapshot['categories'][sec['key']])}권")
        time.sleep(0.4)

    if sum(len(v) for v in snapshot["categories"].values()) == 0:
        sys.exit(f"{key}: 빈 응답 — 이 주간 데이터는 제공되지 않습니다.")

    out = ROOT / "data" / "snapshots" / f"{key}.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {out}")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_site_data
    build_site_data.build()


if __name__ == "__main__":
    main()

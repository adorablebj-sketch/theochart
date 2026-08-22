#!/usr/bin/env python3
"""추천 목록(data/recommendations.json)의 책 정보를 알라딘에서 채워 data/book_meta.json에 캐시한다.

- isbn13이 있으면 ItemLookUp, 없으면 '제목 저자'로 검색해 첫 결과를 쓴다(제목 키로 캐시).
- 이미 캐시된 책은 건너뛴다.
"""
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_rankings import load_dotenv  # noqa: E402

LOOKUP = "https://www.aladin.co.kr/ttb/api/ItemLookUp.aspx"
SEARCH = "https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"


def call(url, params):
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=30) as res:
        text = res.read().decode("utf-8", errors="replace").strip().rstrip(";")
    payload = json.loads(text, strict=False)
    if "errorMessage" in payload:
        raise RuntimeError(payload["errorMessage"])
    return payload.get("item", [])


def to_meta(it):
    cover = it.get("cover", "") or ""
    return {
        "isbn13": str(it.get("isbn13") or ""),
        "title": it.get("title", ""),
        "author": it.get("author", ""),
        "publisher": it.get("publisher", ""),
        "pubDate": it.get("pubDate", ""),
        "cover": cover,
        "coverLarge": cover.replace("cover200", "cover500") if "cover200" in cover else cover,
        "link": it.get("link", ""),
        "description": it.get("description", ""),
        "categoryName": it.get("categoryName", ""),
    }


def title_key(p):
    return "t:" + (p.get("title") or "").strip() + "|" + (p.get("author") or "").strip()


def main():
    load_dotenv()
    key = os.environ.get("ALADIN_TTB_KEY")
    if not key:
        sys.exit("환경변수 ALADIN_TTB_KEY가 필요합니다.")
    rec = json.loads((ROOT / "data" / "recommendations.json").read_text(encoding="utf-8"))
    path = ROOT / "data" / "book_meta.json"
    meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    base = {"ttbkey": key, "output": "js", "Version": "20131101", "Cover": "Big"}
    for p in rec["picks"]:
        isbn = p.get("isbn13")
        k = isbn or title_key(p)
        if k in meta:
            continue
        if isbn:
            items = call(LOOKUP, dict(base, ItemIdType="ISBN13", ItemId=isbn))
        else:
            q = f"{p.get('title', '')} {p.get('author', '')}".strip()
            items = call(SEARCH, dict(base, Query=q, QueryType="Keyword", SearchTarget="Book",
                                      CategoryId=51564, Sort="SalesPoint", MaxResults=5, start=1))
        if items:
            meta[k] = to_meta(items[0])
            print(f"  {p.get('title')}: {meta[k]['title'][:40]} ({meta[k]['isbn13']})")
        else:
            print(f"  {p.get('title')}: 검색 결과 없음")
        time.sleep(0.3)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {path} ({len(meta)}권)")


if __name__ == "__main__":
    main()

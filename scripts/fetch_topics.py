#!/usr/bin/env python3
"""성경 권별(주제별) 차트 수집.

알라딘에는 '요한계시록' 같은 카테고리가 없으므로, 검색 API를 판매지수(SalesPoint)순으로 돌려
권별 순위를 만든다. 통독 교재·필사 노트·만화 같은 잡음은 분류명과 제목 규칙으로 거른다.

사용법:
  python3 scripts/fetch_topics.py          # data/topics.json에서 enabled 주제만
  python3 scripts/fetch_topics.py --all    # 66권 전부
과거 주간 조회는 지원되지 않으므로(검색 API) 매주 실행해 히스토리를 쌓는다.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_rankings import KST, load_dotenv, week_of_month  # noqa: E402

API = "https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
CHRISTIAN_CID = 51564
EXCLUDE_CATEGORY = ("성경공부교재", "어린이/청소년", "쓰기성경", "성경/찬송가", "오디오북", "기독교 교육", "묵상(QT)")
EXCLUDE_TITLE = ("필사", "암송", "만화", "컬러링", "통독", "다이어리", "퍼즐", "낱말", "스티커", "색칠",
                 "책별", "쓰담", "(미니북)", "큐티", "QT", "묵상", "외우", "영어로")
RANGE_RE = re.compile(r"[가-힣][-–][가-힣]|[가-힣0-9]\s*~\s*[가-힣]")  # '고린도전서-요한계시록', '에베소서 2 ~ 디모데전서' 같은 묶음
PARTICLES = "가을를이의는은와과도로에"  # 짧은 권명 뒤에 붙는 조사 — '요나서가', '학개의'
BIBLE_TEXT_RE = re.compile(r"^메시지 ")  # 『메시지 로마서』류는 성경 본문이지 연구서가 아니다
TOP_N = 30
CROSS_TOPIC_LIMIT = 3  # 세 권 이상의 성경에 동시에 잡히면 개론·통독서로 보고 제외


def search(ttb_key, query, start=1, max_results=50):
    params = {
        "ttbkey": ttb_key, "Query": query, "QueryType": "Keyword", "SearchTarget": "Book",
        "CategoryId": CHRISTIAN_CID, "Sort": "SalesPoint", "MaxResults": max_results, "start": start,
        "output": "js", "Version": "20131101", "Cover": "Big",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        text = res.read().decode("utf-8", errors="replace").strip().rstrip(";")
    payload = json.loads(text, strict=False)
    if "errorMessage" in payload:
        raise RuntimeError(f"알라딘 검색 오류 ({query}): {payload['errorMessage']}")
    return payload.get("item", [])


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def has_alias(title: str, alias: str, loose: bool = False) -> bool:
    """긴 권명(또는 loose 주제)은 띄어쓰기를 무시하고 포함 여부로, 두 글자 권명(학개·아가·요나·미가…)은
    '성경해석학 개론'의 '학개' 같은 우연한 일치를 막기 위해 단어 경계와 조사까지 본다."""
    if loose or len(alias) >= 3:
        return squash(alias) in squash(title)
    pattern = r"(?<![가-힣])" + re.escape(alias) + r"서?(?=$|[^가-힣]|[" + PARTICLES + "])"
    return re.search(pattern, title) is not None


def keep(item, topic) -> bool:
    title = item.get("title", "") or ""
    cat = item.get("categoryName", "") or ""
    if any(x in cat for x in EXCLUDE_CATEGORY):
        return False
    if any(x in title for x in EXCLUDE_TITLE):
        return False
    if RANGE_RE.search(title) or BIBLE_TEXT_RE.search(title):
        return False
    return any(has_alias(title, a, topic.get("loose", False)) for a in topic["aliases"])


def to_book(it):
    cover = it.get("cover", "") or ""
    return {
        "id": str(it.get("isbn13") or it.get("isbn") or it.get("itemId")),
        "title": it.get("title", ""),
        "author": it.get("author", ""),
        "publisher": it.get("publisher", ""),
        "pubDate": it.get("pubDate", ""),
        "cover": cover,
        "coverLarge": cover.replace("cover200", "cover500") if "cover200" in cover else cover,
        "link": it.get("link", ""),
        "salesPoint": it.get("salesPoint"),
        "categoryName": it.get("categoryName", ""),
        "description": it.get("description", ""),
    }


def collect(ttb_key, topic):
    seen = {}
    for q in topic["queries"]:
        for start in (1, 2):
            for it in search(ttb_key, q, start=start):
                if not keep(it, topic):
                    continue
                b = to_book(it)
                if b["id"] not in seen:
                    seen[b["id"]] = b
            time.sleep(0.3)
    return sorted(seen.values(), key=lambda b: -(b["salesPoint"] or 0))


def drop_cross_topic(topics: dict) -> dict:
    """여러 권에 동시에 잡히는 개론·통독서를 걷어내고 주제별 상위 TOP_N만 남긴다."""
    count = {}
    for books in topics.values():
        for b in books:
            count[b["id"]] = count.get(b["id"], 0) + 1
    return {k: [b for b in books if count[b["id"]] < CROSS_TOPIC_LIMIT][:TOP_N] for k, books in topics.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="enabled 여부와 상관없이 전부 수집")
    args = ap.parse_args()
    load_dotenv()
    ttb_key = os.environ.get("ALADIN_TTB_KEY")
    if not ttb_key:
        sys.exit("환경변수 ALADIN_TTB_KEY가 필요합니다.")

    cfg = json.loads((ROOT / "data" / "topics.json").read_text(encoding="utf-8"))
    now = datetime.datetime.now(KST)
    key = f"{now.year}-{now.month:02d}-w{week_of_month(now.day)}"
    snapshot = {"week": key, "fetched_at": now.isoformat(timespec="seconds"), "topics": {}}
    for group in cfg["groups"]:
        collected = {}
        for topic in group["topics"]:
            if not (args.all or topic.get("enabled")):
                continue
            collected[topic["key"]] = collect(ttb_key, topic)
        snapshot["topics"].update(drop_cross_topic(collected))  # 개론서 판정은 같은 그룹 안에서만
    for group in cfg["groups"]:
        for topic in group["topics"]:
            books = snapshot["topics"].get(topic["key"])
            if books is not None:
                print(f"  {topic['label']}: {len(books)}권" + (f" | 1위 {books[0]['title'][:30]}" if books else ""))

    out_dir = ROOT / "data" / "topic_snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{key}.json"
    if out.exists():  # 같은 주에 다시 돌리면 기존 주제는 덮어쓰고 나머지는 유지
        old = json.loads(out.read_text(encoding="utf-8"))
        old["topics"].update(snapshot["topics"])
        snapshot["topics"] = old["topics"]
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {out}")

    import build_site_data
    build_site_data.build()


if __name__ == "__main__":
    main()

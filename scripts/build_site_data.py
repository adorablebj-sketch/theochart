#!/usr/bin/env python3
"""data/snapshots/*.json 전체를 읽어 사이트가 쓰는 site/data.json 하나로 빚는다.

순위는 알라딘 판매 순위를 그대로 쓰지 않고 '교리니 점수'로 다시 매긴다 (공식: data/scoring.json).
  점수 = (이번 주 순위 점수 × w1 + 최근 4주 평균 순위 점수 × w2 + 연속 주수 점수 × w3) × 별점 보정
  - 순위 점수: 1위 100점 … 50위 2점
  - 별점 보정은 큐레이션에 평가가 있는 책에만, 우리 책(own)은 보정 없음
"""
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
KST = datetime.timezone(datetime.timedelta(hours=9))
DEFAULT_SCORING = {
    "weights": {"current": 0.5, "trend4": 0.3, "streak": 0.2},
    "streakCap": 12,
    "ratingMultipliers": [[5.0, 1.30], [4.5, 1.22], [4.0, 1.12], [3.5, 1.0], [0, 0.9]],
    "cautionMultiplier": 0.75,
}


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def week_label(key: str) -> str:
    y, m, w = key.split("-")
    return f"{y}년 {int(m)}월 {w[1]}주차"


def split_title(full: str):
    """알라딘 제목은 '제목 - 부제' 꼴. 본제목과 부제를 나눈다."""
    if " - " in full:
        main, sub = full.split(" - ", 1)
        return main.strip(), sub.strip()
    return full.strip(), ""


def clean_author(raw: str) -> str:
    """'홍길동 (지은이), 김철수 (옮긴이)' → '홍길동, 김철수 옮김'"""
    s = raw.replace(" (지은이)", "").replace("(지은이)", "")
    for src, dst in (("(옮긴이)", "옮김"), ("(엮은이)", "엮음"), ("(그림)", "그림"), ("(감수)", "감수"), ("(해설)", "해설")):
        s = s.replace(" " + src, " " + dst).replace(src, dst)
    return " ".join(s.split())


def clean_description(raw: str, limit: int = 700) -> str:
    """알라딘 소개글의 HTML 태그·엔티티를 걷어내고 길이를 다듬는다."""
    import html
    import re
    s = re.sub(r"<br\s*/?>", "\n", raw or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(" ,.") + "…"
    return s


def short_category(raw: str) -> str:
    """'국내도서>종교/역학>기독교(개신교)>기독교(개신교) 목회/신학>설교/성경연구' → '설교/성경연구'"""
    parts = [p.strip() for p in (raw or "").split(">") if p.strip()]
    return parts[-1] if parts else ""


def rank_score(r) -> float:
    return (51 - r) / 50 * 100 if r else 0.0


class SectionHistory:
    """한 분과(또는 주제)의 주간 목록 전체. 연속 주수·추세 계산용."""

    def __init__(self, lists):
        self.lists = lists
        self.pos = [{b["id"]: i + 1 for i, b in enumerate(lst)} for lst in self.lists]

    def streak(self, book_id, idx) -> int:
        n = 0
        for k in range(idx, -1, -1):
            if book_id in self.pos[k]:
                n += 1
            else:
                break
        return n

    def history(self, book_id, idx, weeks=12):
        """최근 weeks주의 판매 순위 목록 (없던 주는 None). 스파크라인용."""
        start = max(0, idx - weeks + 1)
        return [self.pos[k].get(book_id) for k in range(start, idx + 1)]

    def trend(self, book_id, idx, window=4) -> float:
        """최근 window주 평균 순위 점수. 첫 진입 이후 빠진 주는 0점으로 센다."""
        ranks = [self.pos[k].get(book_id) for k in range(max(0, idx - window + 1), idx + 1)]
        first = next((i for i, r in enumerate(ranks) if r), None)
        if first is None:
            return 0.0
        seq = ranks[first:]
        return sum(rank_score(r) if r else 0.0 for r in seq) / len(seq)


def multiplier(c, scoring) -> float:
    if not c or c.get("own"):
        return 1.0
    if c.get("caution"):
        return scoring["cautionMultiplier"]
    rating = c.get("rating")
    if rating is None:
        return 1.0
    for threshold, m in sorted(scoring["ratingMultipliers"], key=lambda t: -t[0]):
        if rating >= threshold:
            return m
    return 1.0


def ranked(hist, idx, curation, scoring):
    w, cap = scoring["weights"], scoring["streakCap"]
    rows = []
    for i, b in enumerate(hist.lists[idx]):
        sales_rank = i + 1
        streak = hist.streak(b["id"], idx)
        base = (w["current"] * rank_score(sales_rank)
                + w["trend4"] * hist.trend(b["id"], idx)
                + w["streak"] * min(streak, cap) / cap * 100)
        score = base * multiplier(curation.get(b["id"]), scoring)
        rows.append({"book": b, "salesRank": sales_rank, "streak": streak, "score": round(score, 1)})
    rows.sort(key=lambda r: (-r["score"], r["salesRank"]))
    for n, r in enumerate(rows):
        r["rank"] = n + 1
    return rows


_EXCLUSIONS = None


def exclusions():
    global _EXCLUSIONS
    if _EXCLUSIONS is None:
        raw = load_json(ROOT / "data" / "exclusions.json", {})
        _EXCLUSIONS = {
            "authors": [a for a in raw.get("authors", []) if a],
            "publishers": [p for p in raw.get("publishers", []) if p],
            "titleKeywords": [t for t in raw.get("titleKeywords", []) if t],
        }
    return _EXCLUSIONS


def excluded(b) -> bool:
    """복음주의·개혁주의 관점에서 차트 범위 밖인 책 (data/exclusions.json)."""
    ex = exclusions()
    author, publisher, title = b.get("author", "") or "", b.get("publisher", "") or "", b.get("title", "") or ""
    return (any(a in author for a in ex["authors"])
            or any(p in publisher for p in ex["publishers"])
            or any(t in title for t in ex["titleKeywords"]))


_RECS = {}  # isbn13 → 이 책을 추천한 사람들 (build()에서 채움)
_CURATED = set()  # 큐레이션(별점)이 있는 책 — 범위 판단에서 무조건 포함
_SCOPE = None


def scope_rules():
    global _SCOPE
    if _SCOPE is None:
        raw = load_json(ROOT / "data" / "scope.json", {})
        _SCOPE = {k: [x for x in raw.get(k, []) if x] for k in (
            "allowTitles", "allowIds", "denyIds", "rescueTitleKeywords", "excludeTitleKeywords",
            "excludeCategories", "softOutCategories", "inTitleKeywords")}
    return _SCOPE


def scope_decision(b):
    """(범위 안인가, 판단 강도 'strong'|'weak', 이유). weak는 검수함에 올린다."""
    s = scope_rules()
    title, cat, bid = b.get("title", "") or "", b.get("categoryName", "") or "", b.get("id")
    if bid in s["allowIds"] or bid in _RECS or bid in _CURATED or any(k in title for k in s["allowTitles"]):
        return True, "strong", "허용목록"
    if bid in s["denyIds"]:
        return False, "strong", "제외목록"
    if any(k in title for k in s["rescueTitleKeywords"]):
        return True, "strong", "제목(신학·원어)"
    if any(k in title for k in s["excludeTitleKeywords"]):
        return False, "strong", "제목(교재·필사 등)"
    if any(k in cat for k in s["excludeCategories"]):
        return False, "strong", "분류 " + short_category(cat)
    if any(k in cat for k in s["softOutCategories"]):
        return False, "weak", "분류 " + short_category(cat)
    if any(k in title for k in s["inTitleKeywords"]):
        return True, "strong", "분류+제목"
    return True, "weak", "분류 " + short_category(cat)


def write_review_queue(snap):
    """최신 주 분과 목록에서 판단이 약한 책을 모아 검수함(JSON + 숨은 페이지)으로 낸다."""
    seen, rows = set(), []
    for key, books in snap["categories"].items():
        if key == "faith":
            continue
        for i, b in enumerate(books):
            if b["id"] in seen:
                continue
            inside, strength, reason = scope_decision(b)
            if strength == "weak":
                seen.add(b["id"])
                rows.append({"id": b["id"], "title": b.get("title", ""), "author": clean_author(b.get("author", "")),
                             "category": short_category(b.get("categoryName", "")), "section": key,
                             "rank": i + 1, "decision": "남김" if inside else "뺌", "reason": reason})
    (ROOT / "data" / "review_queue.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    import html as _html
    trs = "".join(
        f"<tr><td>{r['decision']}</td><td>{_html.escape(r['title'])}</td><td>{_html.escape(r['author'])}</td>"
        f"<td>{_html.escape(r['category'])}</td><td>{_html.escape(r['reason'])}</td><td><code>{r['id']}</code></td></tr>"
        for r in rows)
    page = ("<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='robots' content='noindex'>"
            "<title>검수함</title><link rel='stylesheet' href='style.css'></head><body>"
            "<main class='shell prose'><h1>검수함</h1><p>규칙이 확신하지 못한 책들입니다. 판단이 다르면 "
            "<code>data/scope.json</code>의 allowIds / denyIds에 ISBN을 넣으세요.</p>"
            "<table><tr><th>판정</th><th>제목</th><th>저자</th><th>분류</th><th>근거</th><th>ISBN</th></tr>"
            + trs + "</table></main></body></html>")
    (ROOT / "site" / "review.html").write_text(page, encoding="utf-8")
    return len(rows)


def public_person(r):
    anon = r.get("disclosure") == "익명"
    return {
        "name": (r.get("field", "") + " 추천자") if anon else r.get("name", ""),
        "school": "" if anon else r.get("school", ""),
        "field": r.get("field", ""),
        "status": r.get("status", ""),
    }


def load_recommendations():
    """data/recommendations.json + data/book_meta.json → isbn이 확정된 추천 목록."""
    rec = load_json(ROOT / "data" / "recommendations.json", {"recommenders": [], "picks": []})
    meta = load_json(ROOT / "data" / "book_meta.json", {})
    people = {r["id"]: r for r in rec.get("recommenders", [])}
    picks = []
    for p in rec.get("picks", []):
        person = people.get(p.get("recommender"))
        if not person:
            continue
        key = p.get("isbn13") or ("t:" + (p.get("title") or "").strip() + "|" + (p.get("author") or "").strip())
        m = meta.get(key, {})
        isbn = p.get("isbn13") or m.get("isbn13")
        if not isbn:
            continue
        summary = dict(public_person(person), reason=p.get("reason", ""), top=bool(p.get("top")), level=p.get("level", ""))
        picks.append({"isbn": isbn, "meta": m, "field": p.get("field", "기타"), "summary": summary})
    return rec, picks


def build_picks(rec, picks, curation, chart_entries):
    """추천 집계 → '필독서' 카테고리 데이터. 차트에 있는 책은 그 항목을, 없으면 알라딘 서지 캐시를 쓴다."""
    by_isbn, order = {}, []
    for pk in picks:
        e = by_isbn.get(pk["isbn"])
        if not e:
            src = chart_entries.get(pk["isbn"])
            if src:
                e = {k: src.get(k) for k in ("id", "title", "subtitle", "fullTitle", "author", "publisher", "pubDate",
                                              "cover", "coverLarge", "link", "description", "category")}
            else:
                m = pk["meta"]
                main_title, subtitle = split_title(m.get("title", ""))
                e = {"id": pk["isbn"], "title": main_title, "subtitle": subtitle, "fullTitle": m.get("title", ""),
                     "author": clean_author(m.get("author", "")), "publisher": m.get("publisher", ""),
                     "pubDate": m.get("pubDate", ""), "cover": m.get("cover", ""), "coverLarge": m.get("coverLarge", ""),
                     "link": m.get("link", ""), "description": clean_description(m.get("description", "")),
                     "category": short_category(m.get("categoryName", ""))}
            e.update(recommenders=[], fields=[], delta=None, isNew=False, streak=0)
            if pk["isbn"] in curation:
                e["curation"] = curation[pk["isbn"]]
            by_isbn[pk["isbn"]] = e
            order.append(pk["isbn"])
        e["recommenders"].append(pk["summary"])
        if pk["field"] not in e["fields"]:
            e["fields"].append(pk["field"])
    fields = {}
    for isbn in order:
        e = by_isbn[isbn]
        e["recommendCount"] = len(e["recommenders"])
        e["recScore"] = e["recommendCount"] + 0.5 * sum(1 for r in e["recommenders"] if r["top"])
        for f in e["fields"]:
            fields.setdefault(f, []).append(e)
    out = []
    for name, books in fields.items():
        ranked_books = sorted(books, key=lambda x: (-x["recScore"], x["title"]))
        out.append({"name": name, "books": [dict(b, rank=i + 1) for i, b in enumerate(ranked_books)]})
    return {"recommenders": [public_person(r) for r in rec.get("recommenders", [])], "fields": out}


def rank_lists(lists, curation, scoring):
    """주간 목록들(오래된 순)을 받아 마지막 주 기준 순위·등락·연속주수를 계산한 책 목록을 돌려준다."""
    lists = [[b for b in lst if not excluded(b)] for lst in lists]
    hist = SectionHistory(lists)
    last = len(lists) - 1
    cur = ranked(hist, last, curation, scoring)
    prev = ranked(hist, last - 1, curation, scoring) if last >= 1 else []
    prev_rank = {r["book"]["id"]: r["rank"] for r in prev}
    prev_present = set(hist.pos[last - 1]) if last >= 1 else set()
    out_books = []
    for r in cur:
        b = r["book"]
        is_new = last >= 1 and b["id"] not in prev_present
        delta = None
        if last >= 1 and not is_new and b["id"] in prev_rank:
            delta = prev_rank[b["id"]] - r["rank"]
        main_title, subtitle = split_title(b.get("title", ""))
        entry = dict(b, rank=r["rank"], salesRank=r["salesRank"], score=r["score"],
                     delta=delta, isNew=is_new, streak=r["streak"],
                     history=hist.history(b["id"], last),
                     title=main_title, subtitle=subtitle, fullTitle=b.get("title", ""),
                     author=clean_author(b.get("author", "")),
                     description=clean_description(b.get("description", "")),
                     category=short_category(b.get("categoryName", "")))
        if b["id"] in curation:
            entry["curation"] = curation[b["id"]]
        if b["id"] in _RECS:
            entry["recommenders"] = _RECS[b["id"]]
            entry["recommendCount"] = len(_RECS[b["id"]])
        out_books.append(entry)
    return out_books


COMMENTARY_SERIES = ("NICNT", "NICOT", "WBC", "PNTC", "BECNT", "NIGTC", "NAC", "UBC", "TNTC", "TOTC", "ZECNT", "NIVAC",
                     "틴데일", "엑스포지멘터리", "JPS", "앵커", "호크마", "국제성서주석", "성서주석", "카리스", "BST",
                     "메인 아이디어", "옥스포드 성경", "Hermeneia", "헤르메네이아", "ICC")


def classify_kind(title: str) -> str:
    """권별 차트에서 '주석·강해'만 따로 볼 수 있게 책 종류를 나눈다."""
    t = title or ""
    if "설교" in t and "주석" not in t:
        return "other"
    if "주석" in t or "주해" in t or "강해" in t or any(s in t for s in COMMENTARY_SERIES):
        return "commentary"
    return "other"


def build_topics(curation, scoring):
    """data/topic_snapshots/*.json → site/topics.json (성경 권별 차트)."""
    files = sorted((ROOT / "data" / "topic_snapshots").glob("*.json"))
    if not files:
        return
    snaps = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    cfg = load_json(ROOT / "data" / "topics.json", {"groups": []})
    groups = []
    for g in cfg["groups"]:
        topics = []
        for t in g["topics"]:
            lists = [s["topics"].get(t["key"], []) for s in snaps]
            books = rank_lists(lists, curation, scoring) if any(lists) else []
            for b in books:
                b["kind"] = classify_kind(b.get("fullTitle", ""))
            topics.append({"key": t["key"], "label": t["label"], "part": t.get("part", ""), "books": books})
        groups.append({"key": g["key"], "label": g["label"], "topics": topics})
    data = {
        "generatedAt": datetime.datetime.now(KST).isoformat(timespec="seconds"),
        "week": snaps[-1]["week"],
        "weekLabel": week_label(snaps[-1]["week"]),
        "weeksTracked": len(snaps),
        "sample": False,
        "featured": load_json(ROOT / "data" / "featured.json", []),
        "groups": groups,
    }
    out = ROOT / "site" / "topics.json"
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"빌드: {out} ({sum(len(g['topics']) for g in groups)}개 주제, {len(snaps)}주 추적)")


def build():
    snap_dir = ROOT / "data" / "snapshots"
    files = sorted(snap_dir.glob("*.json"))
    if not files:
        raise SystemExit("스냅샷이 없습니다. fetch_rankings.py 또는 make_mock.py를 먼저 실행하세요.")
    snaps = [json.loads(f.read_text(encoding="utf-8")) for f in files]

    config = load_json(ROOT / "data" / "categories.json", {"sections": []})
    curation = load_json(ROOT / "data" / "curation.json", {})
    featured = load_json(ROOT / "data" / "featured.json", [])
    scoring = load_json(ROOT / "data" / "scoring.json", DEFAULT_SCORING)

    rec, picks = load_recommendations()
    _RECS.clear()
    for pk in picks:
        _RECS.setdefault(pk["isbn"], []).append(pk["summary"])
    _CURATED.clear()
    _CURATED.update(curation.keys())

    sections = []
    chart_entries = {}
    for sec in config["sections"]:
        lists = [s["categories"].get(sec["key"], []) for s in snaps]
        if sec["key"] != "faith":  # 신앙생활 탭만 원본 그대로, 나머지는 '신학책' 범위로
            lists = [[b for b in lst if scope_decision(b)[0]] for lst in lists]
        books = rank_lists(lists, curation, scoring)
        for b in books:
            chart_entries.setdefault(b["id"], b)
        sections.append({"key": sec["key"], "label": sec["label"], "books": books})

    data = {
        "generatedAt": datetime.datetime.now(KST).isoformat(timespec="seconds"),
        "week": snaps[-1]["week"],
        "weekLabel": week_label(snaps[-1]["week"]),
        "weeksTracked": len(snaps),
        "sample": snaps[-1].get("sample", False),
        "scoring": scoring,
        "featured": featured,
        "picks": build_picks(rec, picks, curation, chart_entries),
        "sections": sections,
    }
    out = ROOT / "site" / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"빌드: {out} ({data['weekLabel']}, {len(snaps)}주 추적, 샘플={data['sample']})")
    print(f"검수함: {write_review_queue(snaps[-1])}권 → site/review.html")
    build_topics(curation, scoring)


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""TTB 키가 나오기 전, 사이트 개발용 샘플 스냅샷 8주치를 만든다.

실제 API가 붙으면 data/snapshots/의 mock- 파일을 지우고 fetch_rankings.py로 교체하면 끝.
책 제목은 실존 도서지만 순위·등락은 전부 가상이다 (sample: true로 표시됨).
"""
import datetime
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent.parent
random.seed(42)

POOLS = {
    "total": [
        ("하나님을 아는 지식", "J. I. 패커", "IVP"),
        ("팀 켈러의 기도", "팀 켈러", "두란노"),
        ("순전한 기독교", "C. S. 루이스", "홍성사"),
        ("목적이 이끄는 삶", "릭 워렌", "디모데"),
        ("하나님을 경험하는 삶", "헨리 블랙가비", ""),
        ("천로역정", "존 번연", ""),
        ("예수는 역사다", "리 스트로벨", ""),
        ("하나님의 임재 연습", "로렌스 형제", ""),
        ("놀라운 하나님의 은혜", "필립 얀시", ""),
        ("내가 알지 못했던 예수", "필립 얀시", ""),
        ("광야를 읽다", "이진희", ""),
        ("메시지 성경", "유진 피터슨", "복있는사람"),
        ("팀 켈러, 하나님을 말하다", "팀 켈러", "두란노"),
        ("5가지 사랑의 언어", "게리 채프먼", ""),
    ],
    "theology": [
        ("기독교 강요", "장 칼뱅", ""),
        ("개혁교의학 개요", "헤르만 바빙크", ""),
        ("조직신학", "웨인 그루뎀", ""),
        ("벌코프 조직신학", "루이스 벌코프", ""),
        ("설교와 설교자", "마틴 로이드 존스", ""),
        ("성령의 사역", "싱클레어 퍼거슨", ""),
        ("하나님의 거룩하심", "R. C. 스프로울", ""),
        ("십자가와 구원", "존 스토트", ""),
        ("그리스도의 기도", "토마스 왓슨", ""),
        ("칭의란 무엇인가", "김세윤", ""),
        ("웨스트민스터 소요리문답 강해", "G. I. 윌리암슨", ""),
        ("교리와 설교", "싱클레어 퍼거슨", ""),
    ],
    "commentary": [
        ("로마서 강해", "마틴 로이드 존스", ""),
        ("매튜 헨리 주석", "매튜 헨리", ""),
        ("칼빈 주석", "장 칼뱅", ""),
        ("박윤선 성경주석", "박윤선", ""),
        ("틴데일 신약주석 시리즈", "", ""),
        ("사도행전 강해", "존 스토트", ""),
        ("요한계시록 주석", "그레고리 빌", ""),
        ("고린도전서 주석", "고든 피", ""),
        ("강해설교", "해돈 로빈슨", ""),
        ("에베소서 강해", "마틴 로이드 존스", ""),
    ],
    "faith": [
        ("팀 켈러의 기도", "팀 켈러", "두란노"),
        ("하나님의 임재 연습", "로렌스 형제", ""),
        ("영적 훈련과 성장", "리처드 포스터", ""),
        ("무릎으로 사는 그리스도인", "무명의 그리스도인", ""),
        ("경건한 습관", "도널드 휘트니", ""),
        ("고통에 답하다", "팀 켈러", ""),
        ("일과 영성", "팀 켈러", ""),
        ("안식", "마르바 던", ""),
        ("거룩한 습관", "유진 피터슨", ""),
        ("기도의 사람 조지 뮬러", "조지 뮬러", ""),
        ("주님과 동행하는 하루", "폴 트립", ""),
    ],
    "bible": [
        ("복음과 하나님의 나라", "그레엄 골즈워디", ""),
        ("성경신학", "게르할더스 보스", ""),
        ("구속사와 성경해석", "에드먼드 클라우니", ""),
        ("성경을 어떻게 읽을 것인가", "고든 피", ""),
        ("메시지 성경", "유진 피터슨", "복있는사람"),
        ("창세기 강해", "데릭 키드너", ""),
        ("로마서 주석", "존 머레이", ""),
        ("시편의 기도", "유진 피터슨", ""),
        ("산상수훈 강해", "마틴 로이드 존스", ""),
        ("요한복음 강해", "D. A. 카슨", ""),
    ],
    "intro": [
        ("순전한 기독교", "C. S. 루이스", "홍성사"),
        ("팀 켈러, 하나님을 말하다", "팀 켈러", "두란노"),
        ("예수는 역사다", "리 스트로벨", ""),
        ("기독교의 기본 진리", "존 스토트", ""),
        ("나니아 연대기", "C. S. 루이스", ""),
        ("고통의 문제", "C. S. 루이스", ""),
        ("스크루테이프의 편지", "C. S. 루이스", ""),
        ("살아있는 신앙", "존 스토트", ""),
        ("믿음이 왜 필요한가", "팀 켈러", ""),
        ("첫걸음 신앙", "니키 검블", ""),
    ],
    "history": [
        ("기독교의 발흥", "로드니 스타크", ""),
        ("초대교회사", "후스토 곤잘레스", ""),
        ("종교개혁 이야기", "?", ""),
        ("마틴 루터", "롤런드 베인턴", ""),
        ("칼빈 평전", "?", ""),
        ("청교도 신앙", "제임스 패커", ""),
        ("본회퍼 평전", "에릭 메택시스", ""),
        ("한국교회사", "?", ""),
        ("어거스틴 고백록", "아우구스티누스", ""),
        ("순교자 열전", "존 폭스", ""),
    ],
}


def slug(title: str) -> str:
    return "mock-" + "".join(ch for ch in title if ch.isalnum())


def load_covers():
    path = ROOT / "data" / "mock_covers.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


COVERS = load_covers()


def make_entry(title, author, publisher):
    meta = COVERS.get(slug(title), {})
    return {
        "id": slug(title),
        "title": title,
        "author": author + " 지음" if author and author != "?" else "",
        "publisher": publisher,
        "pubDate": "",
        "cover": meta.get("cover", ""),
        "accent": meta.get("accent"),
        "link": "https://www.aladin.co.kr",
        "salesPoint": None,
        "bestRank": None,
    }


def main():
    snap_dir = ROOT / "data" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    for old in snap_dir.glob("mock-*.json"):
        old.unlink()

    orders = {k: list(range(len(v))) for k, v in POOLS.items()}
    weeks = []
    base = datetime.date(2026, 6, 29)
    for i in range(8):
        d = base + datetime.timedelta(weeks=i)
        weeks.append((d, f"{d.year}-{d.month:02d}-w{(d.day - 1) // 7 + 1}"))

    for wi, (d, key) in enumerate(weeks):
        for k, order in orders.items():
            for _ in range(random.randint(1, 3)):
                a = random.randrange(len(order) - 1)
                order[a], order[a + 1] = order[a + 1], order[a]
            if wi in (3, 6):
                order.append(order.pop(random.randrange(len(order) // 2)))
        snapshot = {
            "week": key,
            "fetched_at": f"{d.isoformat()}T06:30:00+09:00",
            "sample": True,
            "categories": {
                k: [make_entry(*POOLS[k][idx]) for idx in order[:10]]
                for k, order in orders.items()
            },
        }
        path = snap_dir / f"mock-{key}.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
        print("생성:", path.name)

    import build_site_data
    build_site_data.build()


if __name__ == "__main__":
    main()

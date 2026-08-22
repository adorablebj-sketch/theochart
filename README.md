# 신학책 랭킹 (가칭)

공개 주소: https://adorablebj-sketch.github.io/theobook-chart/ (저장소: adorablebj-sketch/theobook-chart)

매일 아침 자동 갱신되는 기독교 서적 주간 차트. 알라딘 오픈API 집계(객관 데이터) 위에
큐레이션 층(별점 · 난이도 입문/중급/심화 · 노선 · 한줄평)을 얹는 구조다.

## 구조

```
data/categories.json        # 사이트 분과 ↔ 알라딘 CID 매핑 (종합 51564 등)
data/aladin_christian_categories.json  # 알라딘 기독교 카테고리 전체 참조
data/snapshots/*.json       # 주간 스냅샷 (mock-* 은 개발용 샘플)
data/curation.json          # 큐레이션: id(isbn13) → 별점/난이도/노선/한줄평/배지
scripts/fetch_rankings.py   # 알라딘 API 수집 → 스냅샷 저장 → data.json 빌드
scripts/backfill.py         # 과거 주간 히스토리 백필
scripts/build_site_data.py  # 스냅샷 전체 → site/data.json (등락·연속주수 계산)
scripts/make_mock.py        # TTB 키 없을 때 샘플 데이터 생성
site/                       # 정적 사이트 (의존성 없음)
.github/workflows/daily.yml # 매일 06:30 KST 수집 + GitHub Pages 배포
```

## 로컬 실행

```
python3 -m http.server 8765 --directory site
```

## 실데이터 전환 (TTB 키 발급 후)

1. `data/snapshots/mock-*.json` 삭제
2. `ALADIN_TTB_KEY=키 python3 scripts/fetch_rankings.py`
3. 히스토리: `ALADIN_TTB_KEY=키 python3 scripts/backfill.py --weeks 52`
4. `data/curation.json`의 키를 실제 isbn13으로 교체

## 배포 (GitHub)

1. 저장소 생성 후 push
2. Settings → Secrets → `ALADIN_TTB_KEY` 등록
3. Settings → Pages → Source를 "GitHub Actions"로
4. Actions 탭에서 daily-rankings 수동 실행(workflow_dispatch)으로 첫 배포

## 남은 결정

- 이름·도메인 (가칭 상태)
- 분별 노트 공개 여부
- 해외 코너(ECPA 월간) 추가 — v2

# Changelog

All notable changes to **trendline-detector** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- min_confidence 조정 및 sliding window 엘리엇 탐색 (완전한 5파가 최근 6-swing window에 없어도 잡기)
- 차트 오버레이 헬퍼 (matplotlib)
- GitHub Actions CI (pytest 자동 실행)

---

## [0.1.0] — 2026-04-18

### Added
- **Swing detection 모듈** (`src/swings/`)
  - `scipy.signal.find_peaks` 기반 스윙 고점/저점 검출
  - ATR(14) 기반 노이즈 필터 (`detect_swings_with_atr_filter`)
  - 교대 강제 로직 (연속 같은 타입 스윙 제거)
- **Trendline fitter** (`src/trendlines/`)
  - 모든 스윙 쌍 조합으로 후보 트렌드라인 생성 (C(n,2))
  - 터치 카운팅 + 위반 페널티 로직
  - 4-컴포넌트 가중 스코어 (touches 35% / span 25% / recency 30% / slope 10%)
  - Top-K 정렬 반환
- **Elliott Wave 분석** (`src/elliott/`)
  - R1/R2/R3 임펄스 규칙 검증 (`validate_impulse`)
  - ABC 수정 파동 검증 (`validate_corrective`)
  - 피보나치 비율 라이브러리 (retracement 0.236~0.786, extension 1.0~2.618)
  - 피보나치 적합도 기반 confidence 스코어링
  - 완성형 + 미완성(wave 5 진행 중) 레이블링 지원
- **JSON Export** (`src/export/`)
  - 통합 detection 결과 스키마 (`schema_version: 0.1.0`)
  - 타 레포(chart-analyzer, backtest-lab)가 소비할 수 있는 포맷
- **CLI 진입점** (`src/detect.py`)
  - `python -m src.detect --ticker NVDA --days 180`
  - yfinance 데이터 자동 페치
  - 멀티 레벨 컬럼 자동 평탄화
- **Pytest 테스트 커버리지** (29개 테스트, 100% 통과)
  - `tests/test_swings.py` (9 테스트)
  - `tests/test_trendlines.py` (6 테스트)
  - `tests/test_elliott.py` (14 테스트)

### Verified (실측 동작 확인)
- **NVDA 180일**: 34 스윙, 서포트 score 0.96 (8 터치)
- **SPY 365일**: 60 스윙, 레지스턴스 score 1.00 (79 터치, 우상향 추세)
- **BTC-USD 180일**: 우하향 레지스턴스 다수 (조정 국면 정확히 포착)
- **TSLA 90일**: 하락 추세선 다수 (최근 약세 반영)

### Fixed
- `scipy.signal.find_peaks`의 `prominences` 키 누락 문제 해결
  (`prominence=(0, None)` 명시 전달로 항상 키 확보)

### Rollback
복원하려면: `git checkout v0.0.0`

---

## [0.0.0] — 2026-04-18

### Added
- 프로젝트 초기화
- README with 알고리즘 개요 + Emergency Rollback SOP
- CHANGELOG.md (Keep a Changelog 표준)
- .gitignore (Python 표준)
- requirements.txt (scipy, numpy, pandas, yfinance)

### Context
- 목적: TrendSpider "Automated Trendline Detection" 기능의 무료 대체
- 순수 함수 라이브러리 (부작용 없음) — 다른 레포가 소비만 함
- 기존 운영 시스템과 **완전 독립**
- Rollback 전략: archive 처리만으로 격리 가능

### Baseline
작업 시작 시점(2026-04-18) 기존 운영 10개 레포 commit SHA는
[backtest-lab CHANGELOG.md](https://github.com/jinhae8971/backtest-lab/blob/main/CHANGELOG.md)에 공통 기록.

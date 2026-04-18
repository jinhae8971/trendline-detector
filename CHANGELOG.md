# Changelog

All notable changes to **trendline-detector** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Swing high/low 검출 (scipy.signal.find_peaks + ATR 필터)
- Linear regression 기반 트렌드라인 피팅
- Trendline 스코어링 (touch count, slope consistency, time span)
- Elliott Wave 5-wave impulse 규칙 검증
- Elliott Wave 3-wave corrective (ABC) 검증
- Fibonacci retracement 기반 wave confidence 계산
- JSON export 포맷 (`chart-analyzer`, `backtest-lab`에서 소비)
- Golden test fixtures (알려진 엘리엇 파동 샘플로 회귀 방지)

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

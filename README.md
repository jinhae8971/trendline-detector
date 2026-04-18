# 📐 trendline-detector

자동 트렌드라인 + 엘리엇 파동 검출 엔진.
TrendSpider의 "Automated Trendline Detection" 기능을 무료로 대체하는 프로젝트.

## 🎯 목적

- OHLCV 데이터에서 **swing high/low 자동 검출**
- 수학적으로 유효한 **트렌드라인 자동 그리기** (최소 3개 접점 원칙)
- **엘리엇 파동 5파 구조** 자동 레이블링 (1-2-3-4-5 + ABC)
- 결과를 JSON으로 export → `chart-analyzer` / `backtest-lab`가 소비

## 📦 기술 스택

- **scipy.signal.find_peaks** — swing high/low 검출
- **numpy** — 선형 회귀로 트렌드라인 계산
- **pandas** — 시계열 처리
- 순수 Python 구현, 외부 유료 서비스 의존성 0

## 🚀 Quick Start

```bash
git clone https://github.com/jinhae8971/trendline-detector.git
cd trendline-detector
pip install -r requirements.txt

# 단일 종목 트렌드라인 검출
python -m src.detect --ticker NVDA --days 180

# 엘리엇 파동 레이블링
python -m src.elliott --ticker SPY --days 365
```

## 📐 알고리즘 개요

### 1. Swing Points 검출
- `scipy.signal.find_peaks`로 로컬 극점 찾기
- ATR 기반 minimum distance 필터 (노이즈 제거)
- 반복적 축약으로 major swing 추출

### 2. Trendline Fitting
- 2개 이상의 swing point 쌍으로 직선 방정식 생성
- **유효성 검증**: 해당 직선 위/아래로 주가가 얼마나 일관되게 움직였는가
- **스코어링**: touch count, slope consistency, time span 가중합
- Top-N 트렌드라인 반환 (TrendSpider는 최대 2000개, 우리는 상위 20개)

### 3. Elliott Wave Labeling
- 5-wave impulse 구조: 1-2-3-4-5 규칙
  - 2파는 1파 100% 되돌림 불가
  - 3파는 1/3/5 중 최단 불가
  - 4파는 1파 영역 침투 불가
- 3-wave corrective: A-B-C
- Fibonacci 비율 기반 scoring (0.382, 0.5, 0.618, 0.786, 1.618)

## 📂 프로젝트 구조

```
trendline-detector/
├── src/
│   ├── swings/          # Swing high/low 검출
│   │   └── detector.py
│   ├── trendlines/      # 트렌드라인 피팅
│   │   ├── fitter.py
│   │   └── scorer.py
│   ├── elliott/         # 엘리엇 파동 인식
│   │   ├── rules.py        # 엘리엇 규칙 (2파/3파/4파)
│   │   ├── fibonacci.py    # Fibonacci ratio 검사
│   │   └── labeler.py
│   ├── export/          # JSON export (다른 레포에서 소비)
│   └── detect.py
├── configs/
├── tests/
│   └── fixtures/        # 알려진 엘리엇 파동 샘플
├── .github/workflows/
├── CHANGELOG.md
└── README.md
```

## 💡 출력 예시

```json
{
  "ticker": "NVDA",
  "analyzed_at": "2026-04-18T10:00:00Z",
  "timeframe": "daily",
  "swings": [
    {"date": "2026-01-10", "price": 120.5, "type": "low"},
    {"date": "2026-02-15", "price": 145.2, "type": "high"}
  ],
  "trendlines": [
    {
      "type": "support",
      "slope": 0.15,
      "start": "2026-01-10",
      "end": "2026-04-18",
      "touch_count": 4,
      "score": 0.87
    }
  ],
  "elliott_wave": {
    "current_wave": "3",
    "pattern": "impulse",
    "labels": [
      {"wave": "1", "start": "2026-01-10", "end": "2026-01-25"},
      {"wave": "2", "start": "2026-01-25", "end": "2026-02-05"},
      {"wave": "3", "start": "2026-02-05", "end": null}
    ],
    "confidence": 0.72
  }
}
```

## 🔄 Emergency Rollback

### 이전 버전으로 즉시 복원
```bash
git log --oneline
git checkout <commit_sha>
```

### 이 레포가 문제될 경우
이 레포는 **순수 함수 라이브러리** (부작용 없음).
archive 처리로 격리 가능하며 기존 10개 운영 레포 무영향.

## 📝 변경 이력

[CHANGELOG.md](./CHANGELOG.md) 참조

## 🔗 관련 프로젝트

- [global-market-orchestrator](https://github.com/jinhae8971/global-market-orchestrator)
- [backtest-lab](https://github.com/jinhae8971/backtest-lab) — 본 레포의 검출 결과를 전략 진입 조건으로 활용
- [chart-analyzer](https://github.com/jinhae8971/chart-analyzer) — 본 레포의 검출 결과를 차트에 오버레이

## 📜 License

Personal use — jinhae8971

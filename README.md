# KRRI 직원 KPI 관리 대시보드

Python Flask와 SQLite로 만든 내부 업무용 KPI 관리 웹앱입니다.

## 실행

`실행.bat`을 더블클릭하거나 이 폴더에서 다음 명령을 실행합니다.

```powershell
python app.py
```

브라우저에서 `http://127.0.0.1:5000`을 엽니다.

## Flask 설치

일반망:

```powershell
python -m pip install -r requirements.txt
```

강의 폴더의 폐쇄망 패키지 사용:

```powershell
python -m pip install --no-index --find-links="..\폐쇄망설치패키지\packages_3.12.5" -r requirements.txt
```

## 주요 기능

- 직원·부서·직급별 KPI 통합 조회
- KPI 목표, 실적, 가중치 등록 및 달성률 자동 계산
- 직원 상세 패널에서 KPI 실적 즉시 수정
- 평가기간·부서·성과등급 필터와 직원 검색
- 성과등급 분포, 본부별 평균, 우선 코칭 대상 분석
- 직원 등록·보관 및 KPI 현황 CSV 내보내기
- SQLite(`kpi.db`) 영구 저장

초기 실행 시 시연용 직원과 KPI 데이터가 자동 생성됩니다. 실제 운영 전 접근 권한, 사용자 인증, 백업 정책을 기관 기준에 맞게 추가하세요.

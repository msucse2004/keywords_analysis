# 파싱 실패 파일 분석

## 테스트 결과

실제 파싱 함수를 테스트한 결과:

### 성공 (실제로는 파싱 가능)
1. `2020.08.30.City Auditor - City Recorder - Council Minutes .PDF` → `2020-08-30` ✅
2. `2022-06-30 PCEF Comm Presentation.PDF` → `2022-06-30` ✅  
3. `Nov. 07, 2018_Voters...` → `2018-11-07` ✅
4. `Apr_2020_Workers...` → `2020-04-01` ✅

### 실패 (파싱 불가능)

#### 1. 날짜 정보가 전혀 없는 파일
- `Example of Text Analysis.pdf` → None
  - **이유**: 파일명에 날짜 정보가 없음

#### 2. 연도만 있고 월일이 없는 파일
- `2019 News.docx`, `2020 News.docx`, `2021 News.docx` 등 → None
  - **이유**: 파일명에 연도만 있고 월/일 정보가 없음
  - 현재 파서는 `YYYY-MM` 형식만 지원하며, `YYYY` 단독 형식은 지원하지 않음
  - **해결 방법**: `YYYY` 형식 지원 추가 필요 (예: `2020` → `2020-01-01`)

#### 3. 월 이름만 있고 연도가 없는 파일
- `March_portland-clean-energy-fund.pdf` → None
  - **이유**: 파일명에 월 이름(`March`)만 있고 연도 정보가 없음
  - `MMM_YYYY` 패턴은 있지만 `MMM` 단독 패턴은 없음
  - **해결 방법**: 폴더 경로에서 연도 추출 (예: `reddit/2022/March_...` → `2022-03-01`)

#### 4. 언더스코어로 시작하는 파일
- `_Dirty, out of control__ Portland_s cleaning...`
- `_I just want to see things turn around__ Hundreds...`
  - **이유**: 파일명이 언더스코어로 시작하여 날짜 패턴이 매칭되지 않음
  - 파일명에 날짜 정보가 포함되어 있지 않음

#### 5. 날짜가 파일명 중간에 있는 파일
- `Clean Energy Jobs Bill_ What Oregonians Need to Know _ r_Portland.pdf`
- `Extra charge on Portland shoppers_ grocery receipts is part of new city-wide clean energy tax _ r_Portland.pdf`
  - **이유**: 파일명에 날짜 정보가 없거나, 날짜 패턴이 매칭되지 않는 위치에 있음

## 권장 사항

1. **YYYY 형식 지원 추가**: 연도만 있는 파일은 해당 연도의 1월 1일로 처리
2. **폴더 경로에서 연도 추출**: 파일명에 연도가 없지만 폴더 경로에 연도가 있으면 사용
3. **MMM 단독 형식 지원**: 월 이름만 있는 경우 폴더 경로에서 연도 추출


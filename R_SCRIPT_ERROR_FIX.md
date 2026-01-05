# R 스크립트 실행 에러 해결 방법

## 에러 원인

에러 메시지:
```
ERROR conda.cli.main_run:execute(127): `conda run Rscript C:\workspace\test\keywords_analysis\r\plot_trends.R` failed.
cannot open file 'output/tables/keyword_topn_by_date.csv': No such file or directory
```

**주요 원인**: Windows에서 `conda run`이 환경 변수를 제대로 전달하지 못하는 경우가 있습니다.

## 문제 분석

1. 파일은 그룹별 디렉토리(`output/tables/{group_name}/`)에 생성됩니다.
2. Python은 환경 변수 `R_TABLES_DIR`에 올바른 경로를 설정합니다.
3. 하지만 Windows에서 `conda run`이 이 환경 변수를 R 스크립트에 전달하지 못할 수 있습니다.

## 해결 방법

### 방법 1: 수정된 코드 사용 (권장)

최신 코드는 다음과 같은 개선사항을 포함합니다:

1. **디버깅 정보 추가**: R 스크립트가 환경 변수 값을 출력합니다.
2. **명확한 에러 메시지**: 파일을 찾을 수 없을 때 더 자세한 정보를 제공합니다.
3. **절대 경로 사용**: 환경 변수에 절대 경로를 설정합니다.

### 방법 2: 수동으로 R 스크립트 실행하여 테스트

에러를 진단하기 위해 직접 R 스크립트를 실행해보세요:

```powershell
# 환경 변수 설정
$env:R_TABLES_DIR = "C:\workspace\test\keywords_analysis\output\tables\news"
$env:R_FIGURES_DIR = "C:\workspace\test\keywords_analysis\output\figures\news"
$env:R_PROJECT_ROOT = "C:\workspace\test\keywords_analysis"

# R 스크립트 실행
conda run -n keyword-analysis Rscript r/plot_trends.R
```

### 방법 3: conda 환경 활성화 후 직접 실행

`conda run` 대신 환경을 활성화한 후 직접 실행:

```powershell
conda activate keyword-analysis

# 환경 변수 설정
$env:R_TABLES_DIR = "C:\workspace\test\keywords_analysis\output\tables\news"
$env:R_FIGURES_DIR = "C:\workspace\test\keywords_analysis\output\figures\news"
$env:R_PROJECT_ROOT = "C:\workspace\test\keywords_analysis"

# R 스크립트 실행
Rscript r/plot_trends.R
```

## 개선 사항

### Python 코드 (`src/news_kw/pipeline.py`)
- 절대 경로 사용
- 디버깅 로그 추가
- stdout과 stderr 모두 로깅

### R 스크립트 (`r/plot_trends.R`, `r/plot_keyword_map.R`, `r/plot_wordcloud.R`)
- 환경 변수 디버깅 출력
- 파일 존재 확인
- 명확한 에러 메시지

## 다음 단계

1. 파이프라인을 다시 실행해보세요.
2. 로그 파일에서 R 스크립트의 환경 변수 출력을 확인하세요.
3. 만약 환경 변수가 여전히 전달되지 않는다면, 방법 2 또는 3을 사용하세요.

## 참고

- Windows에서 `conda run`의 환경 변수 전달은 때때로 문제가 될 수 있습니다.
- R 스크립트의 디버깅 출력을 확인하면 문제를 빠르게 진단할 수 있습니다.
- 모든 경로는 절대 경로를 사용하는 것이 좋습니다.



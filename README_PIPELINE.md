# 파이프라인 실행 가이드

이 프로젝트는 아나콘다(conda) 환경에서 실행되도록 설계되었습니다.

## 실행 방법

### 방법 1: 실행 스크립트 사용 (권장)

Windows에서 가장 간단한 방법은 제공된 실행 스크립트를 사용하는 것입니다:

#### 전체 파이프라인 실행
```bash
# 배치 파일 사용
run_all.bat

# 또는 PowerShell 스크립트 사용
.\run_all.ps1
```

#### 개별 단계 실행

**파일 필터링:**
```bash
run_filter_files.bat
# 또는
.\run_filter_files.ps1
```

**Python 파이프라인:**
```bash
run_pipeline.bat
# 또는
.\run_pipeline.ps1
```

### 방법 2: Makefile 사용

```bash
# 전체 파이프라인
make all

# 개별 단계
make filter_files
make run_py
make fig
```

### 방법 3: 직접 conda run 사용

```bash
# 파일 필터링
conda run -n keyword-analysis python -m news_kw.filter_files --raw_dir data/raw_txt --filtered_dir data/filtered_data --config config/default.yaml

# Python 파이프라인
conda run -n keyword-analysis python -m news_kw.cli --config config/default.yaml --input_dir data/filtered_data --output_dir output --data_dir data
```

## 주의사항

- **반드시 `keyword-analysis` conda 환경에서 실행해야 합니다.**
- 실행 스크립트를 사용하면 자동으로 올바른 conda 환경에서 실행됩니다.
- 직접 Python을 실행할 경우 conda 환경 경고가 표시될 수 있습니다.

## Conda 환경 설정

conda 환경이 없거나 설정되지 않은 경우:

```bash
# 환경 파일로부터 환경 생성
conda env create -f anaconda/env/environment.yml

# 환경 활성화
conda activate keyword-analysis

# 또는 환경 활성화 없이 실행 (권장)
conda run -n keyword-analysis python -m news_kw.cli
```






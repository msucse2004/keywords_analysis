# PyCharm에서 프로젝트 실행하기

## 1. Conda 환경 설정

### 1.1 Conda 환경 확인
먼저 conda 환경이 설치되어 있는지 확인하세요:
```bash
conda env list
```
`keyword-analysis` 환경이 보여야 합니다. 없으면:
```bash
conda env create -f anaconda/env/environment.yml
```

### 1.2 PyCharm에서 Python 인터프리터 설정

1. **File → Settings** (Windows/Linux) 또는 **PyCharm → Preferences** (Mac)
2. **Project: keywords_analysis → Python Interpreter**
3. 톱니바퀴 아이콘 → **Add Interpreter → Add Local Interpreter**
4. **Conda Environment** 선택
5. **Existing environment** 선택
6. **Interpreter** 옆의 폴더 아이콘 클릭
7. 다음 경로를 찾아 선택:
   - Windows: `C:\Users\[사용자명]\anaconda3\envs\keyword-analysis\python.exe`
   - Mac/Linux: `~/anaconda3/envs/keyword-analysis/bin/python`
8. **OK** 클릭하여 인터프리터 설정 완료

## 2. 프로젝트 구조 설정

1. **File → Settings → Project: keywords_analysis → Project Structure**
2. 다음 폴더들을 **Sources**로 표시 (필요시):
   - `src` 폴더
3. **Mark as** 버튼으로 설정

## 3. Run Configuration 생성

### 3.1 메인 파이프라인 실행 설정 (권장: Module name 사용)

1. **Run → Edit Configurations...**
2. **+** 버튼 클릭 → **Python**
3. 설정:
   - **Name**: `Run Pipeline`
   - **Module name**: `news_kw.cli` (Script path가 아님!)
   - **Parameters**: `--config config/default.yaml --input_dir data/filtered_data --output_dir output --data_dir data`
   - **Working directory**: `$PROJECT_DIR$`
   - **Python interpreter**: `keyword-analysis` (conda 환경)

**주의**: Script path를 사용할 경우, 경로가 중복될 수 있습니다. **Module name** 방식을 권장합니다.

### 3.2 파일 필터링 실행 설정

1. **Run → Edit Configurations...**
2. **+** 버튼 클릭 → **Python**
3. 설정:
   - **Name**: `Filter Files`
   - **Module name**: `news_kw.filter_files`
   - **Parameters**: `--raw_dir data/raw_txt --filtered_dir data/filtered_data --config config/default.yaml`
   - **Working directory**: `$PROJECT_DIR$`
   - **Python interpreter**: `keyword-analysis` (conda 환경)

### 3.3 키워드 지연 분석 실행 설정

1. **Run → Edit Configurations...**
2. **+** 버튼 클릭 → **Python**
3. 설정:
   - **Name**: `Keyword Lag Analysis`
   - **Script path**: `$PROJECT_DIR$/analyze_keyword_lag.py`
   - **Working directory**: `$PROJECT_DIR$`
   - **Python interpreter**: `keyword-analysis` (conda 환경)

## 4. 실행 방법

### 방법 1: Run Configuration 사용 (권장)
- 상단의 Run Configuration 드롭다운에서 원하는 설정 선택
- **▶** (Run) 버튼 클릭 또는 `Shift+F10`

### 방법 2: 터미널 사용
PyCharm 하단의 **Terminal** 탭에서:
```bash
# 전체 파이프라인
conda run -n keyword-analysis python -m news_kw.cli --config config/default.yaml --input_dir data/filtered_data --output_dir output --data_dir data

# 파일 필터링
conda run -n keyword-analysis python -m news_kw.filter_files --raw_dir data/raw_txt --filtered_dir data/filtered_data --config config/default.yaml

# 키워드 지연 분석
conda run -n keyword-analysis python analyze_keyword_lag.py
```

### 방법 3: Python 파일에서 직접 실행
- `src/news_kw/cli.py` 파일을 열고
- `main()` 함수 옆에 있는 **▶** 버튼 클릭
- 또는 파일에서 `if __name__ == '__main__':` 부분을 찾아 실행

## 5. 디버깅

1. **Run → Edit Configurations...**
2. 위의 Run Configuration에서 **Allow parallel run** 체크 해제 (디버깅 시)
3. 브레이크포인트 설정 후 **🐛** (Debug) 버튼 클릭

## 6. 주의사항

1. **Conda 환경 필수**: 이 프로젝트는 `keyword-analysis` conda 환경을 사용합니다.
2. **R 패키지**: R 스크립트 실행을 위해 conda 환경에 R 패키지가 설치되어 있어야 합니다.
3. **Working Directory**: 항상 프로젝트 루트(`keywords_analysis`)가 working directory로 설정되어야 합니다.
4. **패키지 설치**: `src/news_kw` 패키지를 editable mode로 설치하려면:
   ```bash
   conda activate keyword-analysis
   pip install -e .
   ```

## 7. 문제 해결

### "can't open file ... cli.pycli.py" 오류 발생 시
**증상**: `cli.pycli.py`처럼 파일명이 중복된 오류

**해결 방법**:
1. **Run → Edit Configurations...** 열기
2. 해당 Configuration 선택
3. **Script path** 대신 **Module name** 사용
   - **Module name**: `news_kw.cli` (Script path 필드가 비어있어야 함)
   - Script path 필드가 채워져 있다면 삭제하고 Module name만 사용

**또는** Script path를 사용할 경우:
- 정확한 경로: `$PROJECT_DIR$/src/news_kw/cli.py` (맨 끝의 `.py`만 한 번!)
- `cli.py`가 두 번 반복되지 않도록 주의

### ModuleNotFoundError 발생 시
```bash
conda activate keyword-analysis
pip install -e .
```

### R 스크립트 실행 실패 시
- Conda 환경에 R 패키지가 설치되어 있는지 확인
- `conda list` 명령으로 R 패키지 확인

### 경로 문제 발생 시
- Working directory가 프로젝트 루트인지 확인
- 상대 경로가 올바른지 확인 (예: `config/default.yaml`, `data/filtered_data`)

### R 스크립트 실행 실패 ("cannot open file 'output/tables/keyword_topn_by_date.csv'") 에러 시

**증상**: 
```
Error in file(file, "rt") : cannot open the connection
cannot open file 'output/tables/keyword_topn_by_date.csv': No such file or directory
```

**원인**: PyCharm Run Configuration에서 Working directory가 프로젝트 루트로 설정되지 않았거나, 환경 변수가 제대로 전달되지 않음

**해결 방법**:
1. **Run → Edit Configurations...** 열기
2. 해당 Configuration 선택
3. **Working directory** 필드 확인:
   - `$PROJECT_DIR$` 또는
   - 프로젝트 루트의 절대 경로 (예: `C:\workspace\keywords_analysis`)
   - **주의**: `C:\workspace\test\keywords_analysis` 같이 다른 경로가 아닌지 확인!

4. Working directory가 올바르게 설정되었는지 확인:
   - PyCharm 하단의 **Run** 탭에서 실제 실행 경로 확인
   - 에러 메시지의 경로가 프로젝트 루트와 일치하는지 확인

5. **Environment variables** 확인 (필요시):
   - Run Configuration에서 **Environment variables** 섹션 확인
   - Python 스크립트가 R 스크립트에 환경 변수를 전달하므로, 직접 설정할 필요는 없지만 확인

**참고**: Python 스크립트(`pipeline.py`)가 R 스크립트를 실행할 때 `R_TABLES_DIR`, `R_FIGURES_DIR`, `R_PROJECT_ROOT` 환경 변수를 자동으로 설정합니다. Working directory만 올바르게 설정하면 됩니다.

### 경로에 "test" 폴더가 나타나는 에러 (C:\workspace\test\keywords_analysis)

**증상**: 
```
ERROR conda.cli.main_run:execute(127): `conda run Rscript C:\workspace\test\keywords_analysis\r\plot_trends.R` failed.
```
경로에 `test` 폴더가 포함되어 나타나는 경우

**원인**: 
- PyCharm에서 잘못된 프로젝트 경로를 열었거나
- 프로젝트가 복사/이동되었는데 PyCharm이 이전 경로를 참조하고 있음

**해결 방법**:
1. **PyCharm에서 올바른 프로젝트 열기**:
   - File → Close Project (현재 프로젝트 닫기)
   - File → Open
   - `C:\workspace\keywords_analysis` 폴더 선택 (중간에 `test` 폴더가 없는 경로!)
   
2. **Run Configuration 확인**:
   - Run → Edit Configurations...
   - Working directory가 `$PROJECT_DIR$` 또는 `C:\workspace\keywords_analysis`인지 확인
   - `C:\workspace\test\keywords_analysis` 같은 잘못된 경로가 아닌지 확인

3. **Project Root 확인**:
   - File → Settings → Project: keywords_analysis → Project Structure
   - Project Root가 `C:\workspace\keywords_analysis`로 표시되는지 확인


# R 패키지 수동 설치 가이드

이 프로젝트에 필요한 R 패키지들을 수동으로 설치하는 방법입니다.

## 프로젝트에 필요한 패키지 목록

- `ggplot2` - 그래프 생성
- `igraph` - 네트워크 그래프 분석
- `ggraph` - 그래프 시각화
- `dplyr` - 데이터 조작
- `yaml` - YAML 파일 읽기
- `viridis` - 색상 팔레트
- `wordcloud` - 워드클라우드 생성

## 설치 방법

### 1. R 콘솔에서 직접 설치 (가장 일반적)

R 또는 RStudio를 열고 다음 명령어를 실행합니다:

```r
# CRAN에서 설치
install.packages(c("ggplot2", "igraph", "ggraph", "dplyr", "yaml", "viridis", "wordcloud"))

# 또는 개별적으로 설치
install.packages("ggplot2")
install.packages("igraph")
install.packages("ggraph")
install.packages("dplyr")
install.packages("yaml")
install.packages("viridis")
install.packages("wordcloud")
```

### 2. 특정 CRAN 미러에서 설치

```r
# 특정 미러 선택
chooseCRANmirror()

# 또는 미러 URL 직접 지정
install.packages("ggplot2", repos = "https://cran.rstudio.com/")
```

### 3. 바이너리 파일(.tar.gz)에서 설치

패키지의 소스 파일(.tar.gz)을 다운로드한 경우:

```r
# 로컬 파일 경로 지정
install.packages("C:/path/to/package.tar.gz", repos = NULL, type = "source")
```

예시:
```r
install.packages("C:/downloads/ggplot2_3.4.0.tar.gz", repos = NULL, type = "source")
```

### 4. GitHub에서 설치 (devtools 필요)

일부 패키지는 GitHub에서만 제공될 수 있습니다:

```r
# devtools가 설치되어 있어야 함
install.packages("devtools")

# GitHub에서 설치
devtools::install_github("hadley/ggplot2")
```

### 5. 오프라인 설치 (인터넷 연결 없음)

#### 5.1 패키지 다운로드 (다른 컴퓨터에서)

```r
# 패키지 및 의존성 다운로드
packages <- c("ggplot2", "igraph", "ggraph", "dplyr", "yaml", "viridis", "wordcloud")
download.packages(packages, destdir = "C:/R_packages", 
                  repos = "https://cran.rstudio.com/", 
                  type = "win.binary")  # Windows의 경우
```

#### 5.2 오프라인 컴퓨터에서 설치

```r
# 다운로드한 패키지 파일들로부터 설치
install.packages(list.files("C:/R_packages", full.names = TRUE), 
                 repos = NULL, 
                 type = "win.binary")
```

### 6. 관리자 권한으로 설치 (Windows)

권한 문제가 발생하는 경우:

1. R 또는 RStudio를 **관리자 권한으로 실행**
2. 설치 명령어 실행

또는 사용자 라이브러리에 설치:

```r
# 사용자 라이브러리 경로 확인
.libPaths()

# 사용자 라이브러리에 설치
install.packages("ggplot2", lib = "C:/Users/YourName/Documents/R/win-library/4.3")
```

### 7. 의존성 패키지와 함께 설치

모든 의존성을 포함하여 설치:

```r
install.packages("ggplot2", dependencies = TRUE)
```

### 8. 특정 버전 설치

```r
# remotes 패키지 필요
install.packages("remotes")

# 특정 버전 설치
remotes::install_version("ggplot2", version = "3.4.0")
```

### 9. 설치 확인

설치가 완료된 후 확인:

```r
# 패키지 로드 테스트
library(ggplot2)
library(igraph)
library(ggraph)
library(dplyr)
library(yaml)
library(viridis)
library(wordcloud)

# 설치된 패키지 목록 확인
installed.packages()
```

### 10. 설치 오류 해결

#### 의존성 패키지 누락 오류
```r
install.packages(c("package_name"), dependencies = TRUE)
```

#### 컴파일 오류 (Windows)
- Rtools 설치 필요
- https://cran.r-project.org/bin/windows/Rtools/ 에서 다운로드

#### 권한 오류
- 관리자 권한으로 R 실행
- 또는 사용자 라이브러리 경로 사용

## Windows에서 Rtools 설치가 필요한 경우

일부 패키지는 컴파일이 필요합니다. Rtools를 먼저 설치하세요:

1. https://cran.r-project.org/bin/windows/Rtools/ 방문
2. R 버전에 맞는 Rtools 다운로드 및 설치
3. 설치 후 R 재시작

설치 확인:
```r
Sys.which("make")
```

## 일괄 설치 스크립트

프로젝트 루트에 `install_r_packages.R` 파일을 만들고 다음 내용을 실행:

```r
# 필요한 패키지 목록
required_packages <- c(
  "ggplot2",
  "igraph",
  "ggraph",
  "dplyr",
  "yaml",
  "viridis",
  "wordcloud"
)

# 설치되지 않은 패키지만 설치
new_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]
if(length(new_packages)) {
  install.packages(new_packages, dependencies = TRUE)
}

# 모든 패키지 로드 확인
for(pkg in required_packages) {
  if(!require(pkg, character.only = TRUE)) {
    cat("패키지", pkg, "설치 또는 로드 실패\n")
  } else {
    cat("패키지", pkg, "로드 성공\n")
  }
}
```

## 참고 링크

- CRAN: https://cran.r-project.org/
- R 패키지 검색: https://cran.r-project.org/web/packages/available_packages_by_name.html
- 패키지 매뉴얼: https://cran.r-project.org/web/packages/



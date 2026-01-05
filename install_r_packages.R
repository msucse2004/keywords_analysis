# R 패키지 자동 설치 스크립트
# 이 스크립트는 프로젝트에 필요한 모든 R 패키지를 설치합니다.

# 필요한 패키지 목록
required_packages <- c(
  "ggplot2",   # 그래프 생성
  "igraph",    # 네트워크 그래프 분석
  "ggraph",    # 그래프 시각화
  "dplyr",     # 데이터 조작
  "yaml",      # YAML 파일 읽기
  "viridis",   # 색상 팔레트
  "wordcloud"  # 워드클라우드 생성
)

cat("=== R 패키지 설치 시작 ===\n\n")

# 설치되지 않은 패키지만 설치
new_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]

if(length(new_packages) > 0) {
  cat("다음 패키지들을 설치합니다:\n")
  cat(paste(new_packages, collapse = ", "), "\n\n")
  
  # CRAN 미러 선택 (대화형 모드에서는 자동 선택)
  if(interactive()) {
    cat("CRAN 미러를 선택합니다...\n")
  }
  
  # 패키지 설치 (의존성 포함)
  install.packages(new_packages, dependencies = TRUE, repos = "https://cran.rstudio.com/")
  
  cat("\n패키지 설치 완료!\n\n")
} else {
  cat("모든 패키지가 이미 설치되어 있습니다.\n\n")
}

# 설치 확인 및 로드 테스트
cat("=== 패키지 로드 테스트 ===\n\n")
failed_packages <- character(0)

for(pkg in required_packages) {
  result <- tryCatch({
    library(pkg, character.only = TRUE)
    cat(sprintf("✓ %-15s - 로드 성공\n", pkg))
    TRUE
  }, error = function(e) {
    cat(sprintf("✗ %-15s - 로드 실패: %s\n", pkg, e$message))
    FALSE
  })
  
  if(!result) {
    failed_packages <- c(failed_packages, pkg)
  }
}

cat("\n=== 설치 결과 요약 ===\n")
cat(sprintf("총 패키지: %d개\n", length(required_packages)))
cat(sprintf("성공: %d개\n", length(required_packages) - length(failed_packages)))
cat(sprintf("실패: %d개\n", length(failed_packages)))

if(length(failed_packages) > 0) {
  cat("\n실패한 패키지:\n")
  cat(paste(failed_packages, collapse = ", "), "\n")
  cat("\n수동으로 설치를 시도해보세요:\n")
  cat("install.packages(c(", paste(paste0('"', failed_packages, '"'), collapse = ", "), "))\n")
} else {
  cat("\n모든 패키지가 성공적으로 설치되고 로드되었습니다!\n")
}

cat("\n=== 스크립트 완료 ===\n")


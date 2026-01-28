# 카카오 채용 정보 자동 크롤러

카카오 채용 API를 활용하여 BUSINESS_SERVICES 정규직 채용 정보를 매일 자동 수집하고 Google Sheets에 적재합니다.

## 수집 대상
- **직군**: 서비스비즈 (BUSINESS_SERVICES)
- **고용형태**: 정규직
- **회사**: 카카오 전체 계열사

## 실행 주기
- 매일 오전 9시 (한국 시간) 자동 실행
- GitHub Actions의 `workflow_dispatch`로 수동 실행 가능

## 설정 방법

### 1. Google Cloud 설정
1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Google Sheets API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. 대상 스프레드시트에 서비스 계정 이메일을 **편집자**로 공유

### 2. GitHub Secrets 등록
Repository Settings > Secrets and variables > Actions에서 다음 시크릿 등록:

| Secret 이름 | 설명 |
|------------|------|
| `GOOGLE_CREDENTIALS` | 서비스 계정 JSON 키 전체 내용 |
| `SPREADSHEET_ID` | Google 스프레드시트 ID (URL에서 `/d/` 뒤의 값) |

### 3. 스프레드시트 ID 찾기
스프레드시트 URL 형식:
```
https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
```

## 스프레드시트 컬럼 구조
| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| 공고ID | 직무명 | 회사 | 근무지 | 고용형태 | 등록일 | 마감일 | 수집일시 |

## 로컬 테스트
```bash
# 환경변수 설정
export GOOGLE_CREDENTIALS='{"type": "service_account", ...}'
export SPREADSHEET_ID='your-spreadsheet-id'

# 실행
pip install -r requirements.txt
python crawler.py
```

## 파일 구조
```
kakao-jobs-crawler/
├── .github/
│   └── workflows/
│       └── crawl.yml          # GitHub Actions 워크플로우
├── crawler.py                 # 크롤링 스크립트
├── requirements.txt           # Python 의존성
└── README.md
```

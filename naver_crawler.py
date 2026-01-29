#!/usr/bin/env python3
"""네이버 채용 정보 크롤러 - Google Sheets 자동 적재"""

import json
import os
from datetime import datetime

import gspread
import requests
from google.oauth2.service_account import Credentials

# API 설정
API_URL = "https://recruit.navercorp.com/rcrt/loadJobList.do"
PARAMS = {
    "subJobCdArr": "3010001,3020001,3030001,3040001,3060001,3070001",  # Service & Business
    "empTypeCdArr": "0010",  # 정규직
}
PAGE_SIZE = 10

# Google Sheets 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def fetch_all_jobs() -> list[dict]:
    """모든 페이지의 채용 정보를 가져옵니다."""
    all_jobs = []
    first_index = 0

    while True:
        params = {**PARAMS, "firstIndex": first_index}
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("result") != "Y":
            raise ValueError(f"API 요청 실패: {data}")

        jobs = data.get("list", [])
        all_jobs.extend(jobs)

        total_size = data.get("totalSize", 0)
        print(f"수집 중... {len(all_jobs)}/{total_size}건")

        if len(all_jobs) >= total_size:
            break
        first_index += PAGE_SIZE

    print(f"총 {len(all_jobs)}건의 채용 공고 수집 완료")
    return all_jobs


def format_date(date_str: str | None) -> str:
    """날짜 문자열(YYYYMMDD)을 포맷팅합니다."""
    if not date_str:
        return "상시채용"
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


def job_to_row(job: dict) -> list[str]:
    """채용 정보를 스프레드시트 행으로 변환합니다."""
    anno_id = str(job.get("annoId", ""))
    url = f"https://recruit.navercorp.com/rcrt/view.do?annoId={anno_id}&lang=ko" if anno_id else ""

    return [
        anno_id,
        job.get("annoSubject", ""),
        job.get("sysCompanyCdNm", ""),
        job.get("subJobCdNm", ""),
        "",  # 근무지 (네이버 API에서 제공 안함)
        job.get("empTypeCdNm", ""),
        format_date(job.get("staYmd")),
        format_date(job.get("endYmd")),
        url,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]


def get_google_spreadsheet():
    """Google Sheets 스프레드시트 객체를 반환합니다."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    spreadsheet_id = os.environ.get("NAVER_SPREADSHEET_ID")

    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS 환경변수가 설정되지 않았습니다.")
    if not spreadsheet_id:
        raise ValueError("NAVER_SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

    creds_data = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    client = gspread.authorize(credentials)

    return client.open_by_key(spreadsheet_id)


def get_or_create_archive_sheet(spreadsheet):
    """Archive 시트를 가져오거나 생성합니다."""
    try:
        return spreadsheet.worksheet("Archive")
    except gspread.WorksheetNotFound:
        archive = spreadsheet.add_worksheet(title="Archive", rows=1000, cols=10)
        header = ["공고ID", "직무명", "회사", "직군", "근무지", "고용형태", "등록일", "마감일", "URL", "수집일시"]
        archive.update("A1:J1", [header])
        print("Archive 시트 생성 완료")
        return archive


def archive_closed_jobs(spreadsheet, active_job_ids: set[str]) -> int:
    """API에서 더 이상 조회되지 않는 공고를 Archive 시트로 이동합니다."""
    sheet = spreadsheet.sheet1
    archive = get_or_create_archive_sheet(spreadsheet)

    all_rows = sheet.get_all_values()
    if len(all_rows) <= 1:
        return 0

    header = all_rows[0]
    data_rows = all_rows[1:]

    rows_to_archive = []
    rows_to_keep = [header]

    for row in data_rows:
        job_id = row[0] if row else ""
        if job_id and job_id not in active_job_ids:
            rows_to_archive.append(row)
        else:
            rows_to_keep.append(row)

    if not rows_to_archive:
        return 0

    archive.append_rows(rows_to_archive, value_input_option="USER_ENTERED")
    sheet.clear()
    sheet.update(f"A1:J{len(rows_to_keep)}", rows_to_keep, value_input_option="USER_ENTERED")

    return len(rows_to_archive)


def setup_header(sheet) -> None:
    """시트에 헤더가 없으면 추가합니다."""
    header = ["공고ID", "직무명", "회사", "직군", "근무지", "고용형태", "등록일", "마감일", "URL", "수집일시"]
    existing = sheet.row_values(1)

    if not existing or existing != header:
        sheet.update("A1:J1", [header])
        print("헤더 설정 완료")


def get_existing_ids(sheet) -> set[str]:
    """이미 등록된 공고 ID 목록을 가져옵니다."""
    try:
        ids = sheet.col_values(1)[1:]  # 헤더 제외
        return set(ids)
    except Exception:
        return set()


def main():
    """메인 실행 함수"""
    print("=== 네이버 채용 정보 크롤러 시작 ===")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 채용 정보 수집
    jobs = fetch_all_jobs()

    if not jobs:
        print("수집된 채용 공고가 없습니다.")
        return

    # 현재 활성 공고 ID 목록
    active_job_ids = set(str(job.get("annoId")) for job in jobs if job.get("annoId"))

    # Google Sheets 연결
    print("\nGoogle Sheets 연결 중...")
    spreadsheet = get_google_spreadsheet()
    sheet = spreadsheet.sheet1
    setup_header(sheet)

    # 마감 공고 아카이브 처리
    archived_count = archive_closed_jobs(spreadsheet, active_job_ids)
    if archived_count > 0:
        print(f"마감 공고 {archived_count}건을 Archive 시트로 이동")

    # 활성 공고 전체 덮어쓰기
    header = ["공고ID", "직무명", "회사", "직군", "근무지", "고용형태", "등록일", "마감일", "URL", "수집일시"]
    all_rows = [header] + [job_to_row(job) for job in jobs]

    sheet.clear()
    sheet.update(f"A1:J{len(all_rows)}", all_rows, value_input_option="USER_ENTERED")

    print(f"\n{len(jobs)}건의 공고를 최신 데이터로 갱신했습니다.")
    print("=== 크롤링 완료 ===")


if __name__ == "__main__":
    main()

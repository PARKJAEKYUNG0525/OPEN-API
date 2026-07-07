"""
서울시 6~7개 자치구 공공서비스예약 JSON 데이터를
policy_location 테이블용 MySQL INSERT SQL로 변환하는 스크립트.

- 시/구 정보를 포함해 정규화하지 않고 통째로 한 테이블에 적재
- '어린이/유아/초등학생/노인(어르신)'만 이용 가능한 항목은 제외
- 실행: python generate_policy_location_sql.py
- 결과: policy_location.sql (CREATE TABLE + INSERT)
"""

import json
import glob
import os
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(__file__)
OUTPUT_PATH = os.path.join(BASE_DIR, "policy_location.sql")

KST = timezone(timedelta(hours=9))

# 이 카테고리들'로만' 구성된 항목은 제외 (어린이/유아/초등학생/노인 전용)
EXCLUDE_ONLY_CATEGORIES = {"어린이", "유아", "초등학생", "어르신", "노인"}


def ms_to_datetime(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=KST).strftime("%Y-%m-%d %H:%M:%S")


def is_excluded(usetgtinfo: str) -> bool:
    """usetgtinfo의 콤마 구분 카테고리가 전부 제외 대상이면 True."""
    if not usetgtinfo:
        return False
    segments = usetgtinfo.split(",")
    categories = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        name = seg.split("(", 1)[0].strip()
        categories.append(name)
    if not categories:
        return False
    return all(cat in EXCLUDE_ONLY_CATEGORIES for cat in categories)


def extract_svc_category(filename: str, gu: str) -> str:
    # 예: "서울시 서대문구 문화행사 공공서비스예약 정보.json" -> "문화행사"
    name = os.path.splitext(filename)[0]
    name = name.replace("서울시", "").replace(gu, "").replace("공공서비스예약", "").replace("정보", "")
    return name.strip()


def sql_str(value):
    if value is None:
        return "NULL"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def sql_num(value):
    if value is None or value == "":
        return "NULL"
    try:
        return repr(float(value))
    except (TypeError, ValueError):
        return "NULL"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS policy_location (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    si VARCHAR(20) NOT NULL,
    gu VARCHAR(20) NOT NULL,
    svc_category VARCHAR(30) NOT NULL,
    svc_id VARCHAR(50) NOT NULL,
    svc_name VARCHAR(255),
    place_name VARCHAR(255),
    max_class_nm VARCHAR(100),
    min_class_nm VARCHAR(100),
    use_tgt_info VARCHAR(255),
    svc_stat_nm VARCHAR(50),
    gubun VARCHAR(20),
    payat_nm VARCHAR(100),
    rcpt_bgn_dt DATETIME NULL,
    rcpt_end_dt DATETIME NULL,
    svc_opn_bgn_dt DATETIME NULL,
    svc_opn_end_dt DATETIME NULL,
    svc_url VARCHAR(500),
    lat DECIMAL(10,7),
    lng DECIMAL(10,7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_svc_id (svc_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()


def main():
    district_dirs = sorted(
        d for d in glob.glob(os.path.join(BASE_DIR, "서울시 *")) if os.path.isdir(d)
    )

    rows = []
    excluded_count = 0
    empty_after_filter_files = []

    for district_dir in district_dirs:
        gu = os.path.basename(district_dir).replace("서울시 ", "").strip()
        json_files = sorted(glob.glob(os.path.join(district_dir, "*.json")))

        for filepath in json_files:
            filename = os.path.basename(filepath)
            svc_category = extract_svc_category(filename, gu)

            with open(filepath, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get("DATA", [])

            for item in items:
                usetgtinfo = (item.get("usetgtinfo") or "").strip()
                if is_excluded(usetgtinfo):
                    excluded_count += 1
                    continue

                rows.append(
                    {
                        "si": "서울시",
                        "gu": gu,
                        "svc_category": svc_category,
                        "svc_id": item.get("svcid"),
                        "svc_name": item.get("svcnm"),
                        "place_name": item.get("placenm"),
                        "max_class_nm": item.get("maxclassnm"),
                        "min_class_nm": item.get("minclassnm"),
                        "use_tgt_info": usetgtinfo,
                        "svc_stat_nm": item.get("svcstatnm"),
                        "gubun": item.get("gubun"),
                        "payat_nm": item.get("payatnm"),
                        "rcpt_bgn_dt": ms_to_datetime(item.get("rcptbgndt")),
                        "rcpt_end_dt": ms_to_datetime(item.get("rcptenddt")),
                        "svc_opn_bgn_dt": ms_to_datetime(item.get("svcopnbgndt")),
                        "svc_opn_end_dt": ms_to_datetime(item.get("svcopnenddt")),
                        "svc_url": item.get("svcurl"),
                        "lat": item.get("y"),
                        "lng": item.get("x"),
                    }
                )

    columns = [
        "si", "gu", "svc_category", "svc_id", "svc_name", "place_name",
        "max_class_nm", "min_class_nm", "use_tgt_info", "svc_stat_nm",
        "gubun", "payat_nm", "rcpt_bgn_dt", "rcpt_end_dt",
        "svc_opn_bgn_dt", "svc_opn_end_dt", "svc_url", "lat", "lng",
    ]
    numeric_cols = {"lat", "lng"}

    lines = [
        "-- policy_location 테이블 생성 및 데이터 적재",
        "-- 자동 생성 스크립트: generate_policy_location_sql.py",
        f"-- 생성 시각: {datetime.now(tz=KST).strftime('%Y-%m-%d %H:%M:%S')}",
        f"-- 전체 원본 건수 대비 제외(어린이/유아/초등학생/노인 전용): {excluded_count}건 제외, {len(rows)}건 적재",
        "",
        CREATE_TABLE_SQL,
        "",
    ]

    batch_size = 200
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        lines.append(f"INSERT INTO policy_location ({', '.join(columns)}) VALUES")
        value_lines = []
        for row in batch:
            values = []
            for col in columns:
                v = row[col]
                values.append(sql_num(v) if col in numeric_cols else sql_str(v))
            value_lines.append(f"({', '.join(values)})")
        lines.append(",\n".join(value_lines) + ";")
        lines.append("")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"적재 대상: {len(rows)}건, 제외: {excluded_count}건")
    print(f"출력 파일: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

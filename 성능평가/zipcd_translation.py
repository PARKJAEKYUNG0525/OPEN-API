import pandas as pd
import re

# 시도명 정규화용
REGION_ALIASES = {
    "서울": "서울특별시",
    "서울시": "서울특별시",
    "부산": "부산광역시",
    "부산시": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


def normalize_text(text: str) -> str:
    """공백 제거 + 기본 문자열 정리"""
    if text is None:
        return ""
    return re.sub(r"\s+", "", str(text).strip())


def normalize_region(region: str) -> str:
    """서울, 전남 같은 축약명을 정식 시도명으로 변환"""
    region = normalize_text(region)

    if region in REGION_ALIASES:
        return REGION_ALIASES[region]

    for short, full in REGION_ALIASES.items():
        if short in region or region in full:
            return full

    return region


def region_to_prefix(region: str) -> str:
    """시도명 → 법정동코드 앞 2자리"""
    region = normalize_region(region)

    prefix_map = {
        "서울특별시": "11",
        "부산광역시": "26",
        "대구광역시": "27",
        "인천광역시": "28",
        "광주광역시": "29",
        "대전광역시": "30",
        "울산광역시": "31",
        "세종특별자치시": "36",
        "경기도": "41",
        "강원특별자치도": "51",
        "충청북도": "43",
        "충청남도": "44",
        "전북특별자치도": "52",
        "전라남도": "46",
        "경상북도": "47",
        "경상남도": "48",
        "제주특별자치도": "50",
    }

    return prefix_map.get(region)


# def get_zipCd(region: str, district: str, csv_path: str) -> str | None:
def get_zipCd(region: str, district: str, df) -> str | None:
    region_prefix = region_to_prefix(region)
    if region_prefix is None:
        return None

    candidates = df[df["시군구코드"].str.startswith(region_prefix)].copy()

    # 세종특별자치시는 시군구코드가 보통 1개라 district와 무관하게 반환
    if region_prefix == "36" and len(candidates) == 1:
        return candidates.iloc[0]["시군구코드"]

    district = normalize_text(district)

    matched = candidates[
        candidates["지역명"].apply(normalize_text).str.contains(district, regex=False)
    ]

    if len(matched) == 0:
        return None

    return matched.iloc[0]["시군구코드"]
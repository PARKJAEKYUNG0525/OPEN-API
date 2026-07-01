import json
import glob
import os
import math
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(__file__)

app = FastAPI()

# 프론트엔드(localhost:5173)에서 이 API를 호출할 수 있도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def ms_to_date(ms):
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def load_all_data():
    all_items = []
    json_files = glob.glob(os.path.join(BASE_DIR, "**", "*.json"), recursive=True)
    for filepath in json_files:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
            items = raw.get("DATA", [])
            all_items.extend(items)
    return all_items


# 서버 시작 시 한 번만 로드 (매 요청마다 파일 다시 읽지 않도록)
ALL_DATA = load_all_data()
print(f"총 {len(ALL_DATA)}건 로드 완료")


def haversine(lat1, lon1, lat2, lon2):
    """두 좌표 사이의 직선거리(km) 계산"""
    R = 6371  # 지구 반지름(km)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def search(keyword: str, data: list):
    keyword = keyword.strip().lower()
    if not keyword:
        return []

    results = []
    for item in data:
        searchable_fields = [
            item.get("svcnm", ""),
            item.get("placenm", ""),
            item.get("minclassnm", ""),
            item.get("maxclassnm", ""),
            item.get("areanm", ""),
        ]
        combined = " ".join(searchable_fields).lower()

        if keyword in combined:
            results.append(item)

    return results


@app.get("/search")
def search_endpoint(
    keyword: str = Query(..., description="검색어"),
    lat: float = Query(None, description="사용자 위도"),
    lng: float = Query(None, description="사용자 경도"),
    radius: float = Query(None, description="반경(km)"),
):
    matched = search(keyword, ALL_DATA)

    results = []
    for item in matched:
        try:
            item_lat = float(item.get("y"))
            item_lng = float(item.get("x"))
        except (TypeError, ValueError):
            continue  # 좌표 없는 데이터는 지도 표시 대상에서 제외

        entry = {
            "지역": item.get("areanm"),
            "서비스명": item.get("svcnm"),
            "장소명": item.get("placenm"),
            "분류": f'{item.get("maxclassnm")} > {item.get("minclassnm")}',
            "서비스상태": item.get("svcstatnm"),
            "접수시작": ms_to_date(item.get("rcptbgndt")),
            "접수종료": ms_to_date(item.get("rcptenddt")),
            "이용시작": ms_to_date(item.get("svcopnbgndt")),
            "이용종료": ms_to_date(item.get("svcopnenddt")),
            "예약URL": item.get("svcurl"),
            "lat": item_lat,
            "lng": item_lng,
        }

        # 위치 + 반경이 주어졌으면 거리 계산 후 필터링
        if lat is not None and lng is not None:
            distance = haversine(lat, lng, item_lat, item_lng)
            entry["거리_km"] = round(distance, 2)

            if radius is not None and distance > radius:
                continue  # 반경 밖이면 제외

        results.append(entry)

    # 위치 정보가 있으면 가까운 순으로 정렬
    if lat is not None and lng is not None:
        results.sort(key=lambda x: x["거리_km"])

    return {"count": len(results), "results": results}


@app.get("/")
def health_check():
    return {"status": "ok", "total_data": len(ALL_DATA)}
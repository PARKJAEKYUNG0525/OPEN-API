import json
import glob
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)

def ms_to_date(ms):
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def load_all_data():
    all_items = []
    # ** 로 하위 폴더까지 재귀 탐색
    json_files = glob.glob(os.path.join(BASE_DIR, "**", "*.json"), recursive=True)

    print(f"발견된 파일 수: {len(json_files)}")

    for filepath in json_files:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
            items = raw.get("DATA", [])
            all_items.extend(items)

    return all_items


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
            item.get("areanm", ""),  # 지역명(구)도 검색 대상에 추가
        ]
        combined = " ".join(searchable_fields).lower()

        if keyword in combined:
            results.append({
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
            })

    return results


if __name__ == "__main__":
    data = load_all_data()
    print(f"총 {len(data)}건 로드 완료")

    while True:
        keyword = input("\n검색어 입력 (종료: q): ")
        if keyword.lower() == "q":
            break

        results = search(keyword, data)
        print(f"\n[검색결과] '{keyword}' → {len(results)}건")
        for r in results:
            print(f"- [{r['지역']}] {r['서비스명']} | {r['서비스상태']} | 접수:{r['접수시작']}~{r['접수종료']}")
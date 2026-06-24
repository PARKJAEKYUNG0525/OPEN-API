# 공공 - 행안부 - 목록
import requests
import json


url = "https://www.youthcenter.go.kr/go/ythip/getPlcy"

params = {
    "apiKeyNm": apiKeyNm,
    "pageNum": 1,
    "pageSize": 2600,
    "pageType": "2",
    "rtnType": "json"
}

response = requests.get(url, params=params)

data = response.json()

# 보기 좋게 저장
with open("support_data_2600.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("저장 완료")
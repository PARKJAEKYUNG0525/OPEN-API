# 공공 - 행안부 - 목록
import requests
import json

apiKeyNm = "b583ca5b-7a0b-4f41-9ed5-d5c73165bc3c"

url = "https://www.youthcenter.go.kr/go/ythip/getPlcy"

params = {
    "apiKeyNm": apiKeyNm,
    "page": 6,
    "perPage": 100
}

response = requests.get(url, params=params)

data = response.json()

# 보기 좋게 저장
with open("support_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("저장 완료")
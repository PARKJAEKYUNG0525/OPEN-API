import requests
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수 가져오기
ontong_api_key = os.getenv("ONTONG_API_KEY")

url = "https://www.youthcenter.go.kr/go/ythip/getPlcy"

params = {
    "apiKeyNm": ontong_api_key,
    "pageNum": 1,
    "pageSize": 2632,
    "pageType": "2",
    "rtnType": "json"
}

response = requests.get(url, params=params)
data = response.json()

with open("support_data_2632.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("저장 완료")
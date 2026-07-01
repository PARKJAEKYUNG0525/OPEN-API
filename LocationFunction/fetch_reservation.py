import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SEOUL_API_KEY")
SERVICE = "ListPublicReservationDetail"
TYPE = "json"
START_INDEX = 1
END_INDEX = 5
SVCID = "여기에_서비스번호_입력"  # 조회하려는 예약 서비스의 SVCID

url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{SVCID}"

response = requests.get(url)
response.raise_for_status()

data = response.json()

with open("result.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("저장 완료 -> result.json")
print(json.dumps(data, ensure_ascii=False, indent=2))
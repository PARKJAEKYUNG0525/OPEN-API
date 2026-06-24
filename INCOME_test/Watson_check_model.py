import os
from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials

load_dotenv()

client = APIClient(Credentials(
    url=os.getenv("WATSON_URL"),
    api_key=os.getenv("WATSON_API_KEY"),
))

# 사용 가능한 전체 모델 목록 출력
specs = client.foundation_models.get_model_specs()
models = specs.get("resources", [])

print(f"총 {len(models)}개 모델\n")
for m in models:
    mid = m.get("model_id", "")
    # 한국어 관련 모델 필터
    if any(k in mid.lower() for k in ["qwen", "solar", "llama", "mistral", "gemma"]):
        print(mid)
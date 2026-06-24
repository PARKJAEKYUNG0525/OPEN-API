import json
import os
from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

WATSON_API_KEY    = os.getenv("WATSON_API_KEY")
WATSON_URL        = os.getenv("WATSON_URL")
WATSON_PROJECT_ID = os.getenv("WATSON_PROJECT_ID")

credentials = Credentials(url=WATSON_URL, api_key=WATSON_API_KEY)
client = APIClient(credentials)

# ── 비교할 모델 3개 ───────────────────────────────────────
MODELS = [
    "mistralai/mistral-medium-2505",
    "mistralai/mistral-small-3-1-24b-instruct-2503",
]

CHAT_PARAMS = {
    "temperature": 0,
    "max_completion_tokens": 256,
}


# ── 핵심 추출 함수 ────────────────────────────────────────
def llm_extract(model, earn_text: str, earn_max: int, earn_min: int, questions: dict) -> list[str]:
    fields_desc = "\n".join(f"- {f}: {questions[f]}" for f in questions)

    amt_hint = ""
    if earn_max > 0 or earn_min > 0:
        amt_hint = f"\n참고: 소득 상한액={earn_max}원, 하한액={earn_min}원 (0이면 없음)"

    prompt = f"""아래 텍스트를 읽고 지원자격 판별에 필요한 항목을 골라주세요.

선택 가능한 항목:
{fields_desc}

【필수 매핑 규칙 - 아래 조건 충족 시 무조건 포함】

1. annual_income 포함 조건 (IF ANY)
   - 텍스트에 "총급여", "연소득", "연간소득", "소득 O원" 등 금액 기준 소득 조건이 있는 경우
   - '소득 상한액' 또는 '소득 하한액'이 0이 아닌 경우
   ※ [예외]: "중위소득"만 단독으로 언급되었거나 소득 언급이 아예 없으면 절대 포함 금지 (FP 방어)

2. is_business_owner 포함 조건 (IF ANY)
   - 텍스트에 "소상공인", "사업자", "창업자", "창업가", "자영업자" 단어가 명시된 경우
   ※ [주의]: 매출액 조건(annual_sales)과 겹치더라도 이 단어들이 보이면 무조건 동시에 포함할 것

3. annual_sales 포함 조건 (IF ANY)
   - 텍스트에 "연매출", "매출액" 단어가 명시된 경우

4. household_income & household_size 포함 조건 (IF ALL)
   - 텍스트에 "중위소득" 단어가 명시된 경우 두 항목을 동시에 포함

【제외 규칙】
- 위 조건에 명시된 핵심 단어나 금액 기준이 텍스트에 직접적으로 등장하지 않는다면 절대 포함하지 마십시오.

텍스트:{amt_hint}
{earn_text}

반드시 아래 JSON 형식만 출력하세요. 다른 텍스트는 절대 출력하지 마세요.
{{"required_fields": ["field1", "field2"]}}"""

    response = model.chat(
        messages=[{"role": "user", "content": prompt}],
        params=CHAT_PARAMS,
    )

    raw = response["choices"][0]["message"]["content"].strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"JSON을 찾을 수 없음: {raw!r}")

    result = json.loads(raw[start:end])
    return result.get("required_fields", [])


# ── 데이터 로드 ───────────────────────────────────────────
with open("question.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

with open("../성능평가/ontongAPI.json", "r", encoding="utf-8") as f:
    data = json.load(f)

policies = data["result"]["youthPolicyList"]

# ── 모델별 실행 ───────────────────────────────────────────
for model_id in MODELS:
    print(f"\n{'='*60}")
    print(f"모델: {model_id}")
    print(f"{'='*60}")

    model = ModelInference(
        model_id=model_id,
        api_client=client,
        project_id=WATSON_PROJECT_ID,
    )

    results = []

    for idx, policy in enumerate(policies, start=1):
        plcy_no  = policy.get("plcyNo", "")
        earn_max = int(policy.get("earnMaxAmt", 0) or 0)
        earn_min = int(policy.get("earnMinAmt", 0) or 0)

        earn_text = f"""
소득조건: {policy.get("earnEtcCn", "")}
추가조건: {policy.get("addAplyQlfcCndCn", "")}
지원내용: {policy.get("plcySprtCn", "")}
""".strip()

        try:
            final_fields = llm_extract(model, earn_text, earn_max, earn_min, questions)
            results.append({
                "plcyNo": plcy_no,
                "required_fields": final_fields,
            })
            print(f"  [{idx}/{len(policies)}] {plcy_no}: {sorted(final_fields)}")

        except Exception as e:
            print(f"  [ERROR] {plcy_no}: {e}")
            results.append({
                "plcyNo": plcy_no,
                "required_fields": [],
                "error": str(e),
            })

    # 모델별 결과 저장
    safe_name = model_id.replace("/", "_").replace("-", "_")
    output_file = f"prediction_Watson_{safe_name}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  → {output_file} 저장 완료")

print("\n\n모든 모델 비교 완료!")
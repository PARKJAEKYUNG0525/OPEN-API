import json
import time
import ollama

MODEL_NAME = "qwen3:8b"


def llm_extract(earn_text: str, earn_max: int, earn_min: int, questions: dict) -> list[str]:
    """LLM만으로 필요한 필드 추출"""
    fields_desc = "\n".join(f"- {f}: {questions[f]}" for f in questions)

    amt_hint = ""
    if earn_max > 0 or earn_min > 0:
        amt_hint = f"\n참고: 소득 상한액={earn_max}원, 하한액={earn_min}원 (0이면 없음)"

    prompt = f"""아래 텍스트를 읽고 지원자격 판별에 필요한 항목을 골라주세요.

선택 가능한 항목:
{fields_desc}

【필수 매핑 규칙 - 아래 조건 충족 시 무조건 포함】

1. annual_income 포함 조건
   - "총급여", "연소득", "연간소득" 등 개인 소득 금액 기준이 있는 경우
   - "월 소득 N만원/천원", "월소득 N만원/천원", "월 평균 소득 N만원" 처럼 월 소득에 금액이 붙은 경우
   - "중위소득 N%" + 금액(천원/만원)이 함께 명시된 경우 → annual_income 반드시 포함
   - 소득 상한액 또는 하한액이 0이 아닌 경우
   ※ [예외]: "중위소득 N%"만 있고 금액이 전혀 없으면 제외

2. household_income + household_size 포함 조건 (반드시 둘 다 동시에 포함)
   - "중위소득", "기준중위소득" 언급 시 둘 다 포함
   - "부부합산", "가구소득", "원가구", "신혼부부" 언급 시 둘 다 포함

3. is_business_owner 포함 조건
   - "소상공인", "사업자", "사업자등록", "창업자", "창업가", "자영업자" 명시
   - 참여제한/제외 대상에 "사업자 제외", "사업자등록이 있는 자" 명시
   ※ [예외]: 단순 지원분야 소개(예: "창업 교육", "사업 안내")에만 등장하면 제외

4. annual_sales 포함 조건
   - "연매출", "매출액" 명시

【제외 규칙】
- 나이, 거주지, 학력, 재직여부만 있으면 모두 제외
- 위 조건 키워드가 텍스트에 없으면 절대 포함 금지

텍스트:{amt_hint}
{earn_text}

반드시 다른 설명이나 문장 없이, 오직 아래 지정된 JSON 형식만 출력하세요.
{{"required_fields": ["field1", "field2"]}}"""

    response = ollama.chat(
        model=MODEL_NAME,
        options={"temperature": 0},
        messages=[{"role": "user", "content": prompt}],
    )

    raw_content = response["message"]["content"].strip()

    start = raw_content.find("{")
    end = raw_content.rfind("}") + 1
    if start == -1 or end == 0:
        return []

    result = json.loads(raw_content[start:end])
    return result.get("required_fields", [])


# ── 메인 루프 ─────────────────────────────────────────────
print(">> 파이썬 스크립트가 실행되었습니다. 데이터를 로드합니다...")

with open("question.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

with open("../성능평가/ontongAPI_50.json", "r", encoding="utf-8") as f:
    data = json.load(f)

policies = data["result"]["youthPolicyList"]
results  = []

print(f">> 데이터 로드 완료! 총 {len(policies)}개의 공고 처리를 시작합니다.\n")

total_start = time.time()

for idx, policy in enumerate(policies, start=1):
    plcy_no  = policy.get("plcyNo", "")
    earn_max = int(policy.get("earnMaxAmt", 0) or 0)
    earn_min = int(policy.get("earnMinAmt", 0) or 0)

    # ✅ 참여제한, 기타사항 추가 (is_business_owner 누락 방지)
    earn_text = f"""
소득조건: {policy.get("earnEtcCn", "")}
추가조건: {policy.get("addAplyQlfcCndCn", "")}
지원내용: {policy.get("plcySprtCn", "")}
참여제한: {policy.get("ptcpPrpTrgtCn", "")}
기타사항: {policy.get("etcMttrCn", "")}
""".strip()

    print(f"[{idx}/{len(policies)}] {plcy_no} 처리 중... ", end="", flush=True)

    policy_start = time.time()

    try:
        final_fields = llm_extract(earn_text, earn_max, earn_min, questions)

        policy_elapsed = time.time() - policy_start

        results.append({
            "plcyNo": plcy_no,
            "required_fields": final_fields,
            "elapsed_sec": round(policy_elapsed, 2),
        })
        print(f"완료 ➔ {sorted(final_fields)}  ⏱ {policy_elapsed:.2f}초")

    except Exception as e:
        policy_elapsed = time.time() - policy_start
        print(f"실패 ➔ 에러 발생: {e}  ⏱ {policy_elapsed:.2f}초")
        results.append({
            "plcyNo": plcy_no,
            "required_fields": [],
            "error": str(e),
            "elapsed_sec": round(policy_elapsed, 2),
        })

total_elapsed = time.time() - total_start
avg_elapsed   = total_elapsed / len(policies)

print(f"\n{'='*50}")
print(f"  전체 소요 시간 : {total_elapsed:.2f}초")
print(f"  공고 평균 시간 : {avg_elapsed:.2f}초")
print(f"  처리 공고 수   : {len(policies)}개")
print(f"{'='*50}")

output_file = "prediction_Ollama(llm_only).json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n>> {output_file} 생성 완료")
import json
import time
import ollama

MODEL_NAME = "qwen3:8b"

# ── 키워드 룰 ─────────────────────────────────────────────
KEYWORD_RULES = {
    "annual_income": [
        "총급여", "연소득", "근로소득", "소득금액", "연봉",
        "월 소득", "월 평균 소득", "월평균소득",
        "건강보험료",
    ],
    "is_business_owner": [
        "소상공인", "사업자등록", "자영업자", "개인사업자", "법인사업자",
        "창업자", "창업가",
    ],
    "annual_sales": [
        "연매출", "매출액",
    ],
    "household_size": [
        "가구원", "가구 인원",
        "중위소득", "기준중위소득", "기준 중위소득",
    ],
    "household_income": [
        "가구소득", "가구 소득", "가구월소득", "가구 월 소득",
        "중위소득", "기준중위소득", "기준 중위소득",
        "부부합산", "신혼부부",
    ],
}

RULE_FIXED_KEYWORDS = {"소상공인", "사업자등록", "자영업자", "개인사업자", "법인사업자"}
BIZ_WEAK_KEYWORDS   = {"창업자", "창업가"}
BIZ_WEAK_FIELDS     = ["earnEtcCn", "addAplyQlfcCndCn", "plcySprtCn",
                        "ptcpPrpTrgtCn", "etcMttrCn", "plcyExplnCn"]


# ── 텍스트 빌더 ───────────────────────────────────────────
def build_search_text(policy: dict) -> str:
    parts = [
        policy.get("earnEtcCn", ""),
        policy.get("addAplyQlfcCndCn", ""),
        policy.get("plcySprtCn", ""),
        policy.get("ptcpPrpTrgtCn", ""),
        policy.get("plcyExplnCn", ""),
    ]
    return "\n".join(p for p in parts if p)

def build_biz_search_text(policy: dict) -> str:
    parts = [
        policy.get("earnEtcCn", ""),
        policy.get("addAplyQlfcCndCn", ""),
        policy.get("plcySprtCn", ""),
        policy.get("ptcpPrpTrgtCn", ""),
        policy.get("plcyExplnCn", ""),
        policy.get("etcMttrCn", ""),
    ]
    return "\n".join(p for p in parts if p)

def build_llm_text(policy: dict) -> str:
    return f"""소득조건: {policy.get("earnEtcCn", "")}
추가조건: {policy.get("addAplyQlfcCndCn", "")}
지원내용: {policy.get("plcySprtCn", "")}
참여제한: {policy.get("ptcpPrpTrgtCn", "")}
기타사항: {policy.get("etcMttrCn", "")}""".strip()


# ── 중위소득 + 금액 동시 존재 여부 판단 ───────────────────
def check_median_with_amount(policy: dict) -> bool:
    combined_text = (
        policy.get("earnEtcCn", "") +
        policy.get("addAplyQlfcCndCn", "") +
        policy.get("plcySprtCn", "")
    )

    is_median_income = any(kw in combined_text for kw in [
        "중위소득", "기준중위소득", "기준 중위소득"
    ])

    amount_patterns = [
        "월소득", "월 소득", "월 평균 소득", "월평균소득",
        "천원", "만원 이하", "만원이하",
    ]
    has_amount = any(p in combined_text for p in amount_patterns)

    return is_median_income and has_amount


# ── 1단계: Rule 후보 추출 ─────────────────────────────────
def get_candidates(policy: dict, earn_max: int, earn_min: int) -> tuple[list[str], bool, bool]:
    search_text     = build_search_text(policy)
    biz_search_text = build_biz_search_text(policy)

    candidates     = set()
    biz_rule_fixed = False

    for field, keywords in KEYWORD_RULES.items():
        if field == "is_business_owner":
            matched_keywords = [kw for kw in keywords if kw in biz_search_text]
            if matched_keywords:
                candidates.add("is_business_owner")
                if any(kw in RULE_FIXED_KEYWORDS for kw in matched_keywords):
                    biz_rule_fixed = True
                else:
                    for field_name in BIZ_WEAK_FIELDS:
                        field_text = policy.get(field_name, "")
                        if any(kw in field_text for kw in BIZ_WEAK_KEYWORDS):
                            biz_rule_fixed = True
                            break
        else:
            if any(kw in search_text for kw in keywords):
                candidates.add(field)

    if earn_max > 0 or earn_min > 0:
        candidates.add("annual_income")

    median_with_amount = check_median_with_amount(policy)
    if median_with_amount:
        candidates.add("annual_income")
        candidates.add("household_income")
        candidates.add("household_size")

    return list(candidates), biz_rule_fixed, median_with_amount


# ── 2단계: LLM 후보 검증 ──────────────────────────────────
def llm_verify(
    llm_text: str,
    candidates: list[str],
    questions: dict,
    biz_rule_fixed: bool,
) -> list[str]:
    if not candidates:
        return []

    candidates_desc = "\n".join(f"- {f}: {questions[f]}" for f in candidates)

    prompt = f"""아래 텍스트를 읽고 후보 항목 중 지원자격 판별에 실제로 필요한 것만 골라주세요.

후보 항목:
{candidates_desc}

판단 기준:
- 텍스트에 명시된 조건만 포함 (추론 금지)
- 총급여, 연소득, 월소득 조건 → annual_income 포함
- 건강보험료로 소득 수준 판단 → annual_income 포함
- 중위소득 조건 + 월소득 금액이 함께 명시 → annual_income 포함
- 소상공인, 사업자등록 언급 (참여제한 포함) → is_business_owner 포함
- 창업자/창업가가 지원 대상 자격 조건으로 명시 → is_business_owner 포함
- 단순 창업 지원 사업 소개, 창업 아이디어 공모 설명에만 등장 → is_business_owner 제외
- 연매출, 매출액 조건 → annual_sales 포함
- 중위소득/기준중위소득 조건 → household_income + household_size 둘 다 포함
- 부부합산, 신혼부부 소득 조건 → household_income + household_size 포함
- 단순 임금/시급/인건비 지급 안내 → annual_income 제외
- 나이/거주지/학력/취업여부만 있으면 모두 제외

반드시 JSON만 출력하세요. 다른 텍스트 절대 금지.

텍스트:
{llm_text}

{{"required_fields": ["field1", "field2"]}}"""

    response = ollama.chat(
        model=MODEL_NAME,
        options={"temperature": 0},
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response["message"]["content"].strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"JSON을 찾을 수 없음: {raw!r}")

    result = json.loads(raw[start:end])
    llm_fields = set(result.get("required_fields", []))

    # ✅ candidates에 있는 것만 허용 (LLM이 없는 필드 추가 방지)
    llm_fields = llm_fields & set(candidates)

    if biz_rule_fixed and "is_business_owner" in candidates:
        llm_fields.add("is_business_owner")

    return list(llm_fields)


# ── 3단계: Rule 후처리 ────────────────────────────────────
def rule_postprocess(
    fields: list[str],
    earn_max: int,
    earn_min: int,
    median_with_amount: bool,
) -> list[str]:
    field_set = set(fields)

    if earn_max > 0 or earn_min > 0:
        field_set.add("annual_income")

    # 중위소득 + 금액 → LLM이 제거했어도 강제 복원
    if median_with_amount:
        field_set.add("annual_income")
        field_set.add("household_income")
        field_set.add("household_size")

    # household_income ↔ household_size 항상 쌍으로
    if "household_income" in field_set:
        field_set.add("household_size")
    if "household_size" in field_set:
        field_set.add("household_income")

    return list(field_set)


# ── 메인 루프 ─────────────────────────────────────────────
with open("question.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

with open("../성능평가/ontongAPI_50.json", "r", encoding="utf-8") as f:
    data = json.load(f)

policies = data["result"]["youthPolicyList"]
results  = []

total_start = time.time()

for idx, policy in enumerate(policies, start=1):
    plcy_no  = policy.get("plcyNo", "")
    earn_max = int(policy.get("earnMaxAmt", 0) or 0)
    earn_min = int(policy.get("earnMinAmt", 0) or 0)

    llm_text = build_llm_text(policy)

    policy_start = time.time()

    try:
        candidates, biz_rule_fixed, median_with_amount = get_candidates(policy, earn_max, earn_min)
        verified_fields = llm_verify(llm_text, candidates, questions, biz_rule_fixed) if candidates else []
        final_fields    = rule_postprocess(verified_fields, earn_max, earn_min, median_with_amount)

        policy_elapsed = time.time() - policy_start

        results.append({
            "plcyNo": plcy_no,
            "required_fields": final_fields,
            "candidates": sorted(candidates),
            "biz_rule_fixed": biz_rule_fixed,
            "llm_verified": sorted(verified_fields),
            "elapsed_sec": round(policy_elapsed, 2),
        })

        print(f"[{idx}/{len(policies)}] {plcy_no}  ⏱ {policy_elapsed:.2f}초")
        print(f"  후보(rule):  {sorted(candidates)}")
        print(f"  검증(LLM):  {sorted(verified_fields)}")
        print(f"  최종:        {sorted(final_fields)}")

    except Exception as e:
        policy_elapsed = time.time() - policy_start
        print(f"[ERROR] {plcy_no}: {e}  ⏱ {policy_elapsed:.2f}초")
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

with open("prediction_Ollama(rule).json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nprediction_Ollama(rule).json 생성 완료")
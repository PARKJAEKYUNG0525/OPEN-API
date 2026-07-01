import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

# Calendar_Test가 아니라 INCOME_test 폴더의 .env를 직접 가리킴
ENV_PATH = Path(r"C:\OPEN-API\INCOME_test\.env")
load_dotenv(dotenv_path=ENV_PATH)

WATSON_API_KEY    = os.getenv("WATSON_API_KEY")
WATSON_URL        = os.getenv("WATSON_URL")
WATSON_PROJECT_ID = os.getenv("WATSON_PROJECT_ID")

credentials = Credentials(url=WATSON_URL, api_key=WATSON_API_KEY)
client = APIClient(credentials)

MODEL_ID = "mistralai/mistral-small-3-1-24b-instruct-2503"
model = ModelInference(
    model_id=MODEL_ID,
    api_client=client,
    project_id=WATSON_PROJECT_ID,
)

print(f"Watson 모델: {MODEL_ID}")
print(f"프로젝트 ID: {WATSON_PROJECT_ID}")

# max_completion_tokens: 128 -> 512로 상향. 공고문 하나에 일정이 여러 개 나오면
# (서류심사/결과발표/면접/기수별 등) JSON 배열이 128 토큰으로는 잘릴 수 있음.
CHAT_PARAMS = {"temperature": 0, "max_completion_tokens": 512}

JSON_PATH = Path(r"C:\OPEN-API\성능평가\ontongAPI_2600.json")
CACHE_PATH = Path(r"C:\OPEN-API\Calendar_Test\ai_schedule_cache.json")

SYSTEM_PROMPT = """한국 청년정책 공고문([정책설명]/[신청방법]/[심사방법])에서 실제 날짜가 명시된
사건만 JSON 배열로 추출하는 도구입니다.

규칙:
- 같은 사건이 여러 섹션에 중복 언급되면 한 번만, 더 구체적인 표현으로 출력
- 같은 날짜에 type 여러 개 부여 금지
- "신청/모집" 관련 type은 aplyYmd가 별도 관리하므로 금지
- raw_text에 실제 날짜 표현이 없으면 추출 금지 (절차 번호, 횟수, "익월"은 날짜 아님)
- "~일 이내", "~후", "상시", "연중", "예산 소진 시까지"처럼 기준일 없는 상대 기간/무기한 표현은 추출 금지
- "OO 기준"처럼 자격요건 판단을 위한 기준 시점은 사용자가 할 일이 아니므로 추출 금지
  (예: "2025.12.22 기준 자격 충족 시 자동 승인"은 자격 판단용 기준일이지 일정이 아님 → 추출 금지)
- "OO일 이전/이후는 OO서류 제출"처럼 서류 종류를 가르는 조건부 안내는 일정이 아니므로 추출 금지
- 일(day) 정보 없으면 지어내지 말고 date는 "YYYY-MM"으로
- 연도 없는 날짜(월/일만 있음)는 [공고 등록연도] 기준 추정. 날짜 자체가 없으면 추정 금지
- 시작일과 종료일이 둘 다 원문에 있을 때만 범위(~)로 출력. 끝 날짜를 지어내지 말 것

type은 다음 중 가장 가까운 것: 서류심사, 결과발표, 면접, 서류등록, 배치통보, 사업개시, 기수별기간

출력 형식: {"type": "...", "date": "YYYY-MM-DD 또는 YYYY-MM 또는 YYYY-MM-DD ~ YYYY-MM-DD", "raw_text": "원문 인용"}
해당 일정 없으면 []. JSON 배열만 출력하고 다른 설명은 절대 포함하지 마세요."""


def find_list_of_dicts(data):
    """JSON 구조 안에서 정책 객체가 담긴 리스트를 재귀적으로 탐색"""
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return data
        return None
    if isinstance(data, dict):
        for value in data.values():
            found = find_list_of_dicts(value)
            if found is not None:
                return found
    return None


def load_policies(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    policies = find_list_of_dicts(data)
    if policies is None:
        raise ValueError("정책 리스트를 찾지 못했습니다.")
    return policies


def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def build_user_prompt(policy: dict) -> str:
    reg_year = (policy.get("frstRegDt") or "")[:4] or "알 수 없음"
    parts = [
        f"[공고 등록연도] {reg_year}",
        f"[정책설명]\n{policy.get('plcyExplnCn', '') or '(없음)'}",
        f"[신청방법]\n{policy.get('plcyAplyMthdCn', '') or '(없음)'}",
        f"[심사방법]\n{policy.get('srngMthdCn', '') or '(없음)'}",
    ]
    return "\n\n".join(parts)


def extract_json_array(text: str) -> list:
    """응답에 ```json 코드펜스나 다른 문장이 섞여도 JSON 배열만 뽑아냄"""
    text = text.strip()
    text = re.sub(r"^```json|^```|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return []


FORBIDDEN_TYPE_SUBSTRINGS = ["신청", "모집"]

# "7. 20." 또는 "7월 20일" 같은 월/일 패턴을 찾아서 (월, 일) 튜플로 반환.
# (?<!\d) / (?!\d) 는 앞뒤에 숫자가 더 붙어있으면 매치하지 않는다는 뜻 —
# "2026. 6. 11."에서 연도 "2026"의 뒷자리 "26"이 "6"이랑 묶여 (26, 6)으로 오인되는 걸 방지
MD_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*(?:[.\-/]|월)\s*(\d{1,2})(?!\d)")


def normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def raw_text_is_grounded(raw_text: str, source_text: str) -> bool:
    """LLM이 인용한 raw_text가 실제 원문(공고문 3개 필드)에 정말 존재하는지 확인.
    공백 차이는 무시하고 부분문자열로 검사 — raw_text를 통째로 지어낸 경우를 걸러내는 가장 기본적인 검증"""
    needle = normalize_for_match(raw_text)
    haystack = normalize_for_match(source_text)
    if not needle:
        return False
    return needle in haystack


def extract_md_pairs(text: str) -> list:
    """텍스트 안의 모든 (월, 일) 쌍을 등장 순서대로 추출"""
    return [(int(m), int(d)) for m, d in MD_PATTERN.findall(text or "")]


MONTH_ONLY_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*월")

# "7.1일 이전은", "OO 이후에는"처럼 날짜를 기준으로 서류 종류/조건을 가르는 표현 —
# 실제 일정이 아니라 조건부 규칙이므로 이 패턴이 있으면 추출 대상에서 제외
CONDITIONAL_RULE_PATTERN = re.compile(r"(이전|이후)(은|는|에는)")


def is_conditional_rule_text(text: str) -> bool:
    return bool(CONDITIONAL_RULE_PATTERN.search(text or ""))


def build_date_from_raw(raw_text: str, reg_year: str) -> str:
    """date는 LLM을 신뢰하지 않고, raw_text 안의 실제 날짜 패턴으로 직접 재구성한다.
    2개 이상 찾으면 첫/마지막을 범위로, 1개면 단일 날짜로, 일자 없이 월만 있으면 'YYYY-MM'으로.
    아무 패턴도 못 찾으면 빈 문자열(추출 실패로 처리)"""
    if not reg_year or not reg_year.isdigit():
        return ""

    pairs = extract_md_pairs(raw_text)

    if len(pairs) >= 2:
        m1, d1 = pairs[0]
        m2, d2 = pairs[-1]
        return f"{reg_year}-{m1:02d}-{d1:02d} ~ {reg_year}-{m2:02d}-{d2:02d}"
    if len(pairs) == 1:
        m, d = pairs[0]
        return f"{reg_year}-{m:02d}-{d:02d}"

    month_only = MONTH_ONLY_PATTERN.search(raw_text or "")
    if month_only:
        return f"{reg_year}-{int(month_only.group(1)):02d}"

    return ""


def clean_events(events: list, raw_full_text: str, reg_year: str) -> list:
    """LLM 출력을 받아 기계적으로 검증/정리 (Rule Engine 역할).
    type만 LLM 결과를 쓰고, date는 raw_text에서 직접 재계산해서 LLM의 날짜 계산을 신뢰하지 않는다."""
    cleaned = []

    for e in events:
        etype = e.get("type") or ""
        raw_text = e.get("raw_text") or ""

        # 0. raw_text 자체가 실제 원문에 없으면(=통째로 지어낸 경우) 무조건 제외
        if not raw_text_is_grounded(raw_text, raw_full_text):
            continue

        # 1. 금지 타입 필터
        if any(bad in etype for bad in FORBIDDEN_TYPE_SUBSTRINGS):
            continue

        # 2. "OO일 이전은/이후는"처럼 조건부 서류·기준 안내 패턴이면 일정이 아니므로 제외
        if is_conditional_rule_text(raw_text):
            continue

        # 3. raw_text에서 날짜를 직접 재구성. LLM이 준 date 필드는 아예 쓰지 않음
        date_str = build_date_from_raw(raw_text, reg_year)
        if not date_str:
            continue

        cleaned.append({"type": etype, "date": date_str, "raw_text": raw_text})

    return cleaned


def extract_schedule(policy: dict, retries: int = 1) -> list:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(policy)},
    ]
    raw_full_text = build_user_prompt(policy)
    reg_year = (policy.get("frstRegDt") or "")[:4]

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = model.chat(messages=messages, params=CHAT_PARAMS)
            content = response["choices"][0]["message"]["content"]
            events = extract_json_array(content)
            return clean_events(events, raw_full_text, reg_year)
        except Exception as e:
            last_error = e
            time.sleep(1)
    raise last_error


def main():
    policies = load_policies(JSON_PATH)
    cache = load_cache()

    # 인자로 준 plcyNo는 캐시에 있어도 무시하고 강제로 다시 호출해서 덮어씀
    # 사용 예: python test.py 20260605005400113228 20260527005400113223
    force_ids = set(sys.argv[1:])
    if force_ids:
        print(f"강제 재처리 대상: {force_ids}")

    total = len(policies)
    skipped = 0
    processed = 0
    failed = 0

    for i, p in enumerate(policies, start=1):
        plcy_no = p.get("plcyNo")
        name = p.get("plcyNm", "(이름 없음)")

        if plcy_no in cache and plcy_no not in force_ids:
            skipped += 1
            continue

        print(f"[{i}/{total}] {name}")

        try:
            events = extract_schedule(p)
            cache[plcy_no] = events
            processed += 1
        except Exception as e:
            print(f"  실패: {e}")
            cache[plcy_no] = {"error": str(e)}
            failed += 1
            continue

        # 50건마다 중간 저장 (중간에 끊겨도 이어서 가능)
        if processed % 50 == 0:
            save_cache(cache)
            print(f"  ...중간 저장 ({processed}건 처리됨)")

    save_cache(cache)
    print(f"\n완료: 신규/재처리 {processed}건 / 스킵(캐시됨) {skipped}건 / 실패 {failed}건")
    print(f"결과 저장 위치: {CACHE_PATH}")


if __name__ == "__main__":
    main()
"""
LLM 평가 스크립트
- Gemini: google-generativeai 사용
- Claude / Ollama: 추후 추가 예정
"""

import json
import time
import pandas as pd
from google import genai
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()

# 설정
BASE_PATH = "C:/OPEN API/성능평가/"

# 환경변수에서 API 키 읽기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# API 키 확인
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

# 모델명
GEMINI_MODEL = "gemini-2.5-flash"

# API 호출 간격 (초)
CALL_DELAY = 1.0

# Gemini 클라이언트 생성
client = genai.Client(api_key=GEMINI_API_KEY)

print("Gemini API 연결 준비 완료")


# 유틸 

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(user: dict, policy: dict) -> str:
    """유저 + 정책 정보를 LLM 프롬프트로 변환"""

    user_str = json.dumps(user, ensure_ascii=False, indent=2)
    policy_str = json.dumps(policy, ensure_ascii=False, indent=2)

    return f"""당신은 청년 정책 지원 자격 심사 전문가입니다.
아래 [정책 정보]와 [지원자 정보]를 읽고, 이 지원자가 해당 정책의 지원 대상에 해당하는지 판단하세요.

판단 규칙:
- 정책의 나이, 지역, 학력, 취업 상태, 혼인 여부, 특수계층 조건을 모두 검토하세요.
- 조건이 명시되지 않거나 "제한없음"인 경우 해당 조건은 통과로 간주합니다.
- 모든 조건을 충족하면 YES, 하나라도 미충족이면 NO로 답하세요.

[정책 정보]
{policy_str}

[지원자 정보]
{user_str}

반드시 아래 형식으로만 답하세요. 다른 말은 절대 쓰지 마세요.
YES
또는
NO"""


def parse_llm_response(response_text: str) -> str:
    """LLM 응답에서 YES/NO 추출"""
    text = response_text.strip().upper()
    if "YES" in text:
        return "YES"
    if "NO" in text:
        return "NO"
    return "UNKNOWN"


# Gemini

def init_gemini():
    return genai.Client(api_key=GEMINI_API_KEY)


def call_gemini(client, prompt: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return parse_llm_response(response.text)
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str:
                wait = (attempt + 1) * 10  # 10초, 20초, 30초
                print(f"  [Gemini 503] {attempt+1}번째 재시도 {wait}초 대기 중...")
                time.sleep(wait)
            else:
                print(f"  [Gemini 오류] {e}")
                return "ERROR"
    print(f"  [Gemini 오류] 최대 재시도 초과")
    return "ERROR"


# Claude (추후 추가)

def call_claude(prompt: str) -> str:
    # TODO: anthropic 패키지 설치 후 구현
    # import anthropic
    # client = anthropic.Anthropic(api_key="...")
    # response = client.messages.create(...)
    raise NotImplementedError("Claude API 키 설정 후 구현 예정")


# Ollama (추후 추가) 

def call_ollama(prompt: str, model: str = "llama3") -> str:
    # TODO: ollama 로컬 서버 띄운 후 구현
    # import requests
    # response = requests.post("http://localhost:11434/api/generate", ...)
    raise NotImplementedError("Ollama 로컬 서버 설정 후 구현 예정")


# 평가 실행 

def evaluate_with_llm(policies, users, call_fn, model_name: str) -> list:
    """
    모든 정책 × 유저 조합을 LLM으로 평가

    call_fn: 프롬프트를 받아 YES/NO를 반환하는 함수
    """
    results = []
    total = len(policies) * len(users)
    count = 0

    for policy in policies:
        policy_id   = policy.get("plcyNo")
        policy_name = policy.get("plcyNm")

        for user in users:
            user_id = user.get("user_id")
            count += 1

            prompt = build_prompt(user, policy)
            result = call_fn(prompt)

            print(f"[{model_name}] ({count}/{total}) policy={policy_id} user={user_id} → {result}")

            results.append({
                "model":       model_name,
                "policy_id":   policy_id,
                "policy_name": policy_name,
                "user_id":     user_id,
                "result":      result,
            })

            time.sleep(CALL_DELAY)

    return results


# 메인 

if __name__ == "__main__":
    # 데이터 로드
    policy_data = load_json(BASE_PATH + "ontongAPI.json")
    dummy_data  = load_json(BASE_PATH + "dummy_data.json")

    policies = policy_data.get("result", {}).get("youthPolicyList", policy_data)
    users    = dummy_data

    policies = policies[:2]   # 정책 2개만
    users    = users[:10]     # 유저 10명만

    print(f"정책 수: {len(policies)}, 유저 수: {len(users)}")
    print(f"총 호출 수: {len(policies) * len(users)}\n")

    # ── Gemini 평가 ──
    gemini_client = init_gemini()
    gemini_results = evaluate_with_llm(
        policies, users,
        call_fn=lambda prompt: call_gemini(gemini_client, prompt),
        model_name="gemini",
    )

    df_gemini = pd.DataFrame(gemini_results)
    df_gemini.to_csv(BASE_PATH + "llm_result_gemini.csv", index=False, encoding="utf-8-sig")
    print(f"\nGemini 결과 저장 완료 → llm_result_gemini.csv ({len(df_gemini)}건)")

    # ── Claude 평가 (추후 활성화) ──
    # claude_results = evaluate_with_llm(
    #     policies, users,
    #     call_fn=call_claude,
    #     model_name="claude",
    # )
    # pd.DataFrame(claude_results).to_csv(BASE_PATH + "llm_result_claude.csv", ...)

    # ── Ollama 평가 (추후 활성화) ──
    # ollama_results = evaluate_with_llm(
    #     policies, users,
    #     call_fn=call_ollama,
    #     model_name="ollama",
    # )
    # pd.DataFrame(ollama_results).to_csv(BASE_PATH + "llm_result_ollama.csv", ...)
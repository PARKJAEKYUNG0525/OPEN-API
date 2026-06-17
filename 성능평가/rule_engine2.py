from zipcd_translation import get_zipCd
import pandas as pd
import json

BASE_PATH = "성능평가/"

zipcd_csv_path = BASE_PATH + "zipcd_mapping.csv"

zipcd_df = pd.read_csv(zipcd_csv_path, dtype={"시군구코드": str})

print(get_zipCd("서울", "성동구", zipcd_df))  # region, district, 코드 파일경로




def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_zip_list(zip_cd):
    if not zip_cd:
        return []

    if isinstance(zip_cd, list):
        return [str(x).strip() for x in zip_cd]

    return [x.strip() for x in str(zip_cd).split(",") if x.strip()]


def is_empty_or_unlimited(value):
    if value is None:
        return True

    value = str(value).strip()

    return value in ["", "제한없음", "제한 없음", "무관", "0"]


# 나이 조건
def match_age(user, policy):
    user_age = user.get("age")

    min_age = policy.get("sprtTrgtMinAge")
    max_age = policy.get("sprtTrgtMaxAge")
    age_limit_yn = policy.get("sprtTrgtAgeLmtYn")

    # 연령 제한 없음
    if age_limit_yn == "N":
        return True

    if user_age is None:
        return False

    user_age = int(user_age)

    if not is_empty_or_unlimited(min_age):
        if user_age < int(min_age):
            return False

    if not is_empty_or_unlimited(max_age):
        if user_age > int(max_age):
            return False

    return True


# 지역 조건
def match_region(user, policy):
    user_region = str(user.get("region", "")).strip()
    user_district = str(user.get("district", "")).strip()
    user_zip = get_zipCd(user_region, user_district, zipcd_df)
    policy_zip_list = parse_zip_list(policy.get("zipCd"))

    # 정책 지역 제한 없음
    if not policy_zip_list:
        return True

    if not user_zip:
        return False

    return user_zip in policy_zip_list

# 혼인 조건
def match_marriage(user, policy):
    user_marriage = user.get("marital_status")
    policy_marriage = policy.get("mrgSttsCd")

    # 제한 없음
    if is_empty_or_unlimited(policy_marriage):
        return True

    # TODO: 실제 코드표에 맞게 수정
    marriage_map = {
        "미혼": "0055002",
        "기혼": "0055001",
        "제한없음": "0055003",
    }

    if policy_marriage == marriage_map.get("제한없음"):
        return True

    return marriage_map.get(user_marriage) == policy_marriage

# 학력 조건
def match_school_status(user, policy):

    user_edu = user.get("education_level")
    policy_school = policy.get("schoolCd")

    if is_empty_or_unlimited(policy_school):
        return True

    school_map = {
        "고졸 미만": "0049001",
        "고교 재학": "0049002",
        "고졸 예정": "0049003",
        "고교 졸업": "0049004",
        "대학 재학": "0049005",
        "대졸 예정": "0049006",
        "대학 졸업": "0049007",
        "석·박사": "0049008",
    }

    if policy_school == "0049010":  # 제한없음
        return True

    return school_map.get(user_edu) == policy_school

# 정책 대상 특수계층
def match_sbiz(user, policy):
    policy_sbiz = policy.get("sbizCd")

    # 값이 없거나 제한없음이면 통과
    if is_empty_or_unlimited(policy_sbiz):
        return True

    if policy_sbiz == "0014010":  # 제한없음
        return True

    # 0014009 기타 → 별도 판단 불가하므로 통과
    if policy_sbiz == "0014009":
        return True

    # 0014001 중소기업
    if policy_sbiz == "0014001":
        return user.get("company_type") == "중소기업"

    # 0014002 여성
    elif policy_sbiz == "0014002":
        return user.get("gender") == "여"

    # 0014003 기초생활수급자
    elif policy_sbiz == "0014003":
        return user.get("special_type") == "기초생활수급자"

    # 0014004 한부모가정
    elif policy_sbiz == "0014004":
        return user.get("special_type") == "한부모가정"

    # 0014005 장애인
    elif policy_sbiz == "0014005":
        return user.get("disability", False) is True

    # 0014006 농업인
    elif policy_sbiz == "0014006":
        return (
            user.get("occupation") == "농업인"
            or user.get("employment_status") == "영농종사자"
        )

    # 0014007 군인
    elif policy_sbiz == "0014007":
        return user.get("military_status") in ["군필", "현역"]

    # 0014008 지역인재
    elif policy_sbiz == "0014008":
        # 지역인재 여부를 더미데이터에 추가했다면 사용
        return (
            user.get("special_type") == "지역인재"
            or user.get("local_talent", False) is True
        )

    # 알 수 없는 코드면 보수적으로 탈락 처리
    return False

# 학과
def match_major(user, policy):
    user_major = user.get("major")
    policy_major = policy.get("plcyMajorCd")

    if is_empty_or_unlimited(policy_major):
        return True

    major_map = {
        "인문계열": "0011001",
        "사회계열": "0011002",
        "상경계열": "0011003",
        "이학계열": "0011004",
        "공학계열": "0011005",
        "예체능계열": "0011006",
        "제한없음": "0011007",
    }

    if policy_major == major_map.get("제한없음"):
        return True

    return major_map.get(user_major) == policy_major

# 취업 상태
def match_job(user, policy):
    policy_job = policy.get("jobCd")

    if is_empty_or_unlimited(policy_job):
        return True

    if policy_job == "0013010":  # 제한없음
        return True

    user_job_codes = set()

    # 재직자
    if user.get("employment_status") == "재직":
        user_job_codes.add("0013001")

    # 미취업자
    elif user.get("employment_status") in [
        "미취업",
        "취업준비생"
    ]:
        user_job_codes.add("0013003")

    # 자영업자
    if user.get("employment_status") == "자영업":
        user_job_codes.add("0013002")

    # (예비)창업자
    if user.get("startup_interest") is True or user.get("occupation") == "창업자":
        user_job_codes.add("0013006")

    return policy_job in user_job_codes

# 소득 조건
def match_income(user, policy):
    user_income = user.get("income")

    earn_min = policy.get("earnMinAmt")
    earn_max = policy.get("earnMaxAmt")
    earn_condition = policy.get("earnCndSeCd")

    # 소득 제한 없음
    if is_empty_or_unlimited(earn_condition):
        return True

    if user_income is None:
        return False

    user_income = int(user_income)

    if not is_empty_or_unlimited(earn_min):
        if user_income < int(earn_min):
            return False

    if not is_empty_or_unlimited(earn_max):
        if user_income > int(earn_max):
            return False

    return True

# 한명의 사용자가 한 개의 정책에 부합하는지 검사
def match_policy(user, policy):
    checks = {
        "age": match_age(user, policy),
        "region": match_region(user, policy),
        "marriage": match_marriage(user, policy),
        # "income": match_income(user, policy),
        "school_status": match_school_status(user, policy),
        "sbiz": match_sbiz(user, policy),
        "job": match_job(user, policy),
        # "major": match_major(user, policy),
        # "military_service": match_military_service(user, policy),
        # "disability": match_disability(user, policy),
        # "startup_intent": match_startup_intent(user, policy),
        # "business_status": match_business_status(user, policy),
        # "employment_status": match_employment_status(user, policy),
    }

    is_matched = all(checks.values())

    return {
        "result": "YES" if is_matched else "NO",
        "details": checks
    }

# 모든 사용자 X 모든 정책 조합을 검사해서 결과를 만드는 함수
def evaluate_all_policies(policy_json_path, dummy_json_path):
    policy_data = load_json(policy_json_path)
    dummy_data = load_json(dummy_json_path)

    # 온통청년 API 구조 대응
    policies = policy_data.get("result", {}).get("youthPolicyList", policy_data)
    users = dummy_data

    results = []

    for policy in policies:
        policy_id = policy.get("plcyNo")
        policy_name = policy.get("plcyNm")

        for user in users:
            user_id = user.get("user_id")

            match_result = match_policy(user, policy)

            results.append({
                "policy_id": policy_id,
                "policy_name": policy_name,
                "user_id": user_id,
                "result": match_result["result"],
                "age_match": match_result["details"]["age"],
                "region_match": match_result["details"]["region"],
                "marriage_match": match_result["details"]["marriage"],
                "school_status": match_result["details"]["school_status"],
                "sbiz": match_result["details"]["sbiz"],
                "job": match_result["details"]["job"],
            })

    return results


if __name__ == "__main__":
    results = evaluate_all_policies(
        policy_json_path=BASE_PATH + "ontongAPI.json",
        dummy_json_path=BASE_PATH + "dummy_data.json"
    )

    df = pd.DataFrame(results)

    df.to_csv(BASE_PATH + "rule_engine_result.csv", index=False, encoding="utf-8-sig")

    print(df.head())
    print("총 결과 수:", len(df))
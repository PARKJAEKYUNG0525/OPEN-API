from zipcd_translation import get_zipCd
import pandas as pd
import json

from code_mapping import (
    JOB_MAP,
    SCHOOL_MAP,
    MARRIAGE_MAP,
    SBIZ_MAP,
    MAJOR_MAP,
)

BASE_PATH = "성능평가/"

zipcd_csv_path = BASE_PATH + "zipcd_mapping.csv"
zipcd_df = pd.read_csv(zipcd_csv_path, dtype={"시군구코드": str})

print(get_zipCd("서울", "성동구", zipcd_df))




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
    return str(value).strip() in ["", "제한없음", "제한 없음", "무관", "0"]


# sbiz 체커 (모듈 레벨에 한 번만 정의)

SBIZ_USER_CHECK = {
    "중소기업":      lambda u: u.get("company_type") == "중소기업",
    "여성":          lambda u: u.get("gender") == "여",
    "기초생활수급자": lambda u: u.get("special_type") == "기초생활수급자",
    "한부모가정":    lambda u: u.get("special_type") == "한부모가정",
    "장애인":        lambda u: u.get("disability") is True,
    "농업인":        lambda u: (
        u.get("occupation") == "농업인"
        or u.get("employment_status") == "영농종사자"
    ),
    "군인":          lambda u: u.get("military_status") in ["군필", "현역"],
    "지역인재":      lambda u: (
        u.get("special_type") == "지역인재"
        or u.get("local_talent") is True
    ),
}


# ── match 함수들 ──────────────────────────────────────────────────────────────

def match_age(user, policy):
    """나이 조건"""
    age_limit_yn = policy.get("sprtTrgtAgeLmtYn")
    if age_limit_yn == "Y":
        return True

    user_age = user.get("age")
    if user_age is None:
        return False
    user_age = int(user_age)

    min_age = policy.get("sprtTrgtMinAge")
    max_age = policy.get("sprtTrgtMaxAge")

    if not is_empty_or_unlimited(min_age) and user_age < int(min_age):
        return False
    if not is_empty_or_unlimited(max_age) and user_age > int(max_age):
        return False

    return True


def match_region(user, policy):
    """지역 조건"""
    policy_zip_list = parse_zip_list(policy.get("zipCd"))
    if not policy_zip_list:
        return True

    user_zip = get_zipCd(
        str(user.get("region", "")).strip(),
        str(user.get("district", "")).strip(),
        zipcd_df,
    )
    if not user_zip:
        return False

    return user_zip in policy_zip_list


def match_marriage(user, policy):
    """혼인 조건"""
    policy_marriage = policy.get("mrgSttsCd")
    if is_empty_or_unlimited(policy_marriage):
        return True

    allowed_value = MARRIAGE_MAP.get(policy_marriage)
    if allowed_value is None:   # 제한없음 (0055003)
        return True

    return user.get("marital_status") == allowed_value


def match_school_status(user, policy):
    """학력 조건"""
    policy_school = policy.get("schoolCd")
    if is_empty_or_unlimited(policy_school):
        return True

    allowed_value = SCHOOL_MAP.get(policy_school)
    if allowed_value is None:   # 제한없음 (0049010)
        return True

    return user.get("education") == allowed_value


def match_sbiz(user, policy):
    """정책 대상 특수계층"""
    policy_sbiz = policy.get("sbizCd")
    if is_empty_or_unlimited(policy_sbiz):
        return True

    allowed_value = SBIZ_MAP.get(policy_sbiz)
    if allowed_value is None:   # 제한없음 (0014010)
        return True
    if allowed_value == "기타":  # 0014009, 판단 불가 → 통과
        return True

    checker = SBIZ_USER_CHECK.get(allowed_value)
    return checker(user) if checker else False


def match_major(user, policy):
    """학과 조건"""
    policy_major = policy.get("plcyMajorCd")
    if is_empty_or_unlimited(policy_major):
        return True

    allowed_value = MAJOR_MAP.get(policy_major)
    if allowed_value is None:   # 제한없음
        return True

    return user.get("major") == allowed_value


def match_job(user, policy):
    """취업 상태 조건"""
    policy_job = policy.get("jobCd")
    if is_empty_or_unlimited(policy_job):
        return True

    # jobCd가 콤마로 여러 개 올 수 있음
    policy_job_codes = [c.strip() for c in str(policy_job).split(",") if c.strip()]

    for code in policy_job_codes:
        allowed_statuses = JOB_MAP.get(code)

        if allowed_statuses is None:    # 제한없음 (0013010)
            return True

        # 창업 관련 (0013006): startup_interest 또는 occupation으로 판단
        if code == "0013006":
            if (
                user.get("startup_interest") is True
                or user.get("occupation") == "창업자"
            ):
                return True
            continue

        if user.get("employment_status") in allowed_statuses:
            return True

    return False


def match_income(user, policy):
    """소득 조건"""
    earn_condition = policy.get("earnCndSeCd")
    if is_empty_or_unlimited(earn_condition):
        return True

    user_income = user.get("income")
    if user_income is None:
        return False
    user_income = int(user_income)

    earn_min = policy.get("earnMinAmt")
    earn_max = policy.get("earnMaxAmt")

    if not is_empty_or_unlimited(earn_min) and user_income < int(earn_min):
        return False
    if not is_empty_or_unlimited(earn_max) and user_income > int(earn_max):
        return False

    return True


# 평가 

def match_policy(user, policy):
    """한 명의 사용자가 한 개의 정책에 부합하는지 검사"""
    checks = {
        "age":          match_age(user, policy),
        "region":       match_region(user, policy),
        "marriage":     match_marriage(user, policy),
        "school_status": match_school_status(user, policy),
        "sbiz":         match_sbiz(user, policy),
        "job":          match_job(user, policy),
        # "income":     match_income(user, policy),
        # "major":      match_major(user, policy),
    }

    is_matched = all(checks.values())

    return {
        "result": "YES" if is_matched else "NO",
        "details": checks,
    }


def evaluate_all_policies(policy_json_path, dummy_json_path):
    """모든 사용자 × 모든 정책 조합을 검사해서 결과 반환"""
    policy_data = load_json(policy_json_path)
    dummy_data = load_json(dummy_json_path)

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
                "policy_id":      policy_id,
                "policy_name":    policy_name,
                "user_id":        user_id,
                "result":         match_result["result"],
                "age_match":      match_result["details"]["age"],
                "region_match":   match_result["details"]["region"],
                "marriage_match": match_result["details"]["marriage"],
                "school_status":  match_result["details"]["school_status"],
                "sbiz":           match_result["details"]["sbiz"],
                "job":            match_result["details"]["job"],
            })

    return results


if __name__ == "__main__":
    results = evaluate_all_policies(
        policy_json_path=BASE_PATH + "ontongAPI.json",
        dummy_json_path=BASE_PATH + "dummy_data.json",
    )

    df = pd.DataFrame(results)
    df.to_csv(BASE_PATH + "rule_engine_result.csv", index=False, encoding="utf-8-sig")

    # 정책별 YES/NO 집계
    count_df = (
        df.groupby(["policy_id", "policy_name", "result"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # YES / NO 컬럼이 없을 경우 대비
    for col in ["YES", "NO"]:
        if col not in count_df.columns:
            count_df[col] = 0

    count_df = count_df[["policy_id", "policy_name", "YES", "NO"]]
    count_df["total"] = count_df["YES"] + count_df["NO"]

    count_df.to_csv(BASE_PATH + "rule_engine_result_count.csv", index=False, encoding="utf-8-sig")

    print(df.head())
    print("총 결과 수:", len(df))
    print("\n[정책별 YES/NO 집계]")
    print(count_df.to_string(index=False))
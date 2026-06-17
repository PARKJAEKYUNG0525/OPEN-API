import os
import json
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

users_path = os.path.join(BASE_DIR, "dummy_data.json")
policy_path = os.path.join(BASE_DIR, "ontongAPI.json")

print(users_path)
print(policy_path)

from code_mapping import (
    JOB_MAP,
    SCHOOL_MAP,
    MARRIAGE_MAP,
    SBIZ_MAP
)


def check_eligibility(user, policy):
    """
    사용자 1명과 공고 1개를 비교하여
    지원 가능 여부(YES / NO)를 반환
    """

    # =========================
    # 1. 나이 조건
    # =========================
    # sprtTrgtAgeLmtYn = "Y" 이면서 min/max 가 둘 다 "0"이면 나이 제한 없음
    # sprtTrgtAgeLmtYn = "N" 이면 나이 제한 없음
    age_limit_yn = policy.get("sprtTrgtAgeLmtYn", "N")
    min_age = policy.get("sprtTrgtMinAge")
    max_age = policy.get("sprtTrgtMaxAge")

    if age_limit_yn == "Y":
        min_age_int = int(min_age) if min_age not in [None, ""] else 0
        max_age_int = int(max_age) if max_age not in [None, ""] else 0

        # 둘 다 0이면 나이 제한 없음으로 간주
        if not (min_age_int == 0 and max_age_int == 0):
            if min_age_int > 0 and user.get("age", 0) < min_age_int:
                return "NO"
            if max_age_int > 0 and user.get("age", 0) > max_age_int:
                return "NO"

    # =========================
    # 2. 취업 조건
    # =========================
    job_cd = policy.get("jobCd")

    if job_cd and job_cd != "0013010":  # 제한없음 제외

        allowed = JOB_MAP.get(job_cd)

        if allowed is not None:
            if user.get("employment_status") not in allowed:
                return "NO"

    # =========================
    # 3. 학력 조건
    # =========================
    school_cd = policy.get("schoolCd")

    if school_cd and school_cd != "0049010":

        allowed = SCHOOL_MAP.get(school_cd)

        if allowed is not None:
            if user.get("education") != allowed:
                return "NO"

    # =========================
    # 4. 결혼 여부
    # =========================
    marriage_cd = policy.get("mrgSttsCd")

    if marriage_cd and marriage_cd != "0055003":

        allowed = MARRIAGE_MAP.get(marriage_cd)

        if allowed is not None:
            if user.get("marital_status") != allowed:
                return "NO"

    # =========================
    # 5. 특수 대상
    # =========================
    sbiz_cd = policy.get("sbizCd")

    if sbiz_cd and sbiz_cd != "0014010":

        special = SBIZ_MAP.get(sbiz_cd)

        if special == "장애인":
            if not user.get("disability", False):
                return "NO"

        elif special == "군인":
            # 군인 조건: 현역(군필) 또는 군 관련 신분
            if user.get("military_status") not in ["군필", "현역"]:
                return "NO"

        elif special == "여성":
            if user.get("gender") != "여":
                return "NO"

        elif special == "기초생활수급자":
            if user.get("special_type") != "기초생활수급자":
                return "NO"

        elif special == "한부모가정":
            if user.get("special_type") != "한부모가정":
                return "NO"

        elif special == "농업인":
            if user.get("employment_status") != "영농종사자":
                return "NO"

        elif special == "지역인재":
            # 지역인재는 별도 필드 없으므로 통과 처리
            pass

    # =========================
    # 6. 지역 조건
    # =========================
    # zipCd가 없거나 빈 값이면 전국 정책으로 간주
    # 2023년 강원특별자치도 출범으로 강원 코드가 42xxx → 51xxx로 변경됨
    # district(시군구명) → zipCd 직접 매핑으로 정확도 향상

    zip_cd_raw = policy.get("zipCd", "")

    if zip_cd_raw not in [None, ""]:
        allowed_zips = set(zip_cd_raw.split(","))

        # district(시군구명) → zipCd 매핑 테이블
        # 강원특별자치도는 구(42xxx)·신(51xxx) 코드 모두 포함
        DISTRICT_ZIP_MAP = {
            # 서울
            "강남구": "11680", "서초구": "11650", "마포구": "11440",
            "종로구": "11110", "성동구": "11200", "광진구": "11215",
            "노원구": "11350", "은평구": "11380", "중구": "11140",
            # 부산
            "해운대구": "26350", "수영구": "26380", "사하구": "26230",
            "동래구": "26260", "부산진구": "26170", "남구": "26290",
            # 대구
            "수성구": "27290", "달서구": "27290", "동구": "27140",
            # 인천
            "연수구": "28185", "남동구": "28200", "부평구": "28237",
            "계양구": "28245",
            # 광주
            "광산구": "29200", "북구": "29170", "서구": "29155",
            # 대전
            "유성구": "30230", "서구": "30170",
            # 경기
            "수원시 팔달구": "41115", "성남시 수정구": "41131",
            "고양시 덕양구": "41281", "용인시 기흥구": "41463", "부천시": "41190",
            # 강원 (구 코드 42xxx + 신 코드 51xxx 모두 포함)
            "춘천시":  ["42110", "51110"],
            "원주시":  ["42130", "51130"],
            "강릉시":  ["42150", "51150"],
            "동해시":  ["42170", "51170"],
            "태백시":  ["42180", "51180"],
            "속초시":  ["42190", "51190"],
            "삼척시":  ["42210", "51230"],  # ← 핵심: 51230 추가
            "홍천군":  ["42710", "51720"],
            "횡성군":  ["42720", "51730"],
            "영월군":  ["42730", "51750"],
            "평창군":  ["42740", "51760"],
            "정선군":  ["42750", "51770"],
            "철원군":  ["42760", "51780"],
            "화천군":  ["42770", "51790"],
            "양구군":  ["42780", "51800"],
            "인제군":  ["42790", "51810"],
            "고성군":  ["42800", "51820"],
            "양양군":  ["42820", "51830"],
            # 충북
            "청주시 상당구": "43111", "충주시": "43130",
            # 충남
            "천안시 동남구": "44131", "아산시": "44200",
            # 전북
            "전주시 완산구": "45111", "익산시": "45140",
            # 전남
            "순천시": "46150", "목포시": "46110",
            # 경북
            "포항시 북구": "47113", "구미시": "47190",
            # 경남
            "창원시 성산구": "48123", "진주시": "48170",
            # 제주
            "제주시": "50110", "서귀포시": "50130",
            # 세종
            "세종시": "36110",
        }

        user_district = user.get("district", "")
        user_region   = user.get("region", "")

        # district 기반 매핑 우선 시도
        district_zips = DISTRICT_ZIP_MAP.get(user_district)

        if district_zips is not None:
            # 리스트(강원 구/신 코드 모두)이거나 단일 문자열
            if isinstance(district_zips, list):
                matched = any(z in allowed_zips for z in district_zips)
            else:
                matched = district_zips in allowed_zips
        else:
            # district 매핑 없으면 시도(region) prefix로 fallback
            REGION_ZIP_PREFIX = {
                "서울": ["111", "114", "117", "112", "113", "115", "116", "118", "119"],
                "부산": ["261", "262", "263", "264", "265", "266", "267", "268", "269"],
                "대구": ["271", "272", "273", "274", "275", "276", "277"],
                "인천": ["281", "282", "283", "284", "285", "286", "287", "288"],
                "광주": ["291", "292", "293", "294", "295"],
                "대전": ["301", "302", "303", "304", "305"],
                "울산": ["311", "312", "313", "314"],
                "세종": ["361"],
                "경기": ["411", "412", "413", "414", "415", "416", "417", "418", "419"],
                "강원": ["421", "422", "423", "424", "425", "426",   # 구 코드
                         "511", "512", "513", "514", "515", "516", "517", "518"],  # 신 코드
                "충북": ["431", "432", "433", "434", "435"],
                "충남": ["441", "442", "443", "444", "445", "446", "447", "448"],
                "전북": ["451", "452", "453", "454", "455"],
                "전남": ["461", "462", "463", "464", "465", "467", "468", "469"],
                "경북": ["471", "472", "473", "474", "475", "477", "478", "479"],
                "경남": ["481", "482", "483", "484", "485", "487", "488", "489"],
                "제주": ["501", "503"],
            }
            prefixes = REGION_ZIP_PREFIX.get(user_region, [])
            matched = any(z[:3] in prefixes for z in allowed_zips)

        if not matched:
            return "NO"

    # =========================
    # 7. 중위소득 조건
    # =========================
    # policy.incomeLimit: 중위소득 기준 (예: 120 → 중위소득 120% 이하)
    # user.household_income_ratio: 중위소득 대비 비율 (%)

    income_limit = policy.get("incomeLimit")

    if income_limit not in [None, ""]:
        if user.get("household_income_ratio", 999) > int(income_limit):
            return "NO"

    # =========================
    # 8. 무주택 조건
    # =========================
    # policy.needHousing: True이면 무주택자만 신청 가능
    # user.housing_status: "무주택", "월세", "전세", "자가", "부모와 거주" 등

    need_housing = policy.get("needHousing")

    if need_housing:
        # 무주택으로 간주하는 상태
        HOMELESS_STATUS = {"무주택", "월세", "전세", "임대주택", "기숙사"}
        if user.get("housing_status") not in HOMELESS_STATUS:
            return "NO"

    # =========================
    # 9. 1인가구 조건
    # =========================
    # policy.singleHousehold: True이면 1인가구만 신청 가능
    # user.household_size: 가구원 수 (정수)

    single_household = policy.get("singleHousehold")

    if single_household:
        if user.get("household_size", 999) != 1:
            return "NO"

    # =========================
    # 10. 회사 유형 조건
    # =========================
    # policy.companyType: "중소기업", "스타트업" 등
    # user.company_type: 동일 문자열 또는 None

    company_type = policy.get("companyType")

    if company_type not in [None, ""]:
        if user.get("company_type") != company_type:
            return "NO"

    # =========================
    # 11. 창업 연차 조건
    # =========================
    # policy.startupYears: 창업 후 최대 허용 연수 (예: 3 → 창업 3년 이하)
    # user.startup_years: 창업 연차 (정수 또는 None)
    # startup_years가 None이면 창업자가 아닌 것으로 판단 → 창업 조건 정책은 NO

    startup_limit = policy.get("startupYears")

    if startup_limit not in [None, ""]:
        user_startup_years = user.get("startup_years")
        if user_startup_years is None:
            # 창업자가 아님
            return "NO"
        if user_startup_years > int(startup_limit):
            return "NO"

    # =========================
    # 12. 정책 참여 횟수 제한
    # =========================
    # policy.maxPrevious: 이전 정책 참여 허용 횟수 (예: 0 → 최초 신청자만)
    # user.previous_policy_count: 기존 참여 횟수 (없으면 0으로 간주)

    max_previous = policy.get("maxPrevious")

    if max_previous not in [None, ""]:
        if user.get("previous_policy_count", 0) > int(max_previous):
            return "NO"

    # =========================
    # 자유서술 조건 (추후 확장 예정)
    # =========================
    # earnEtcCn       → 소득 기타 조건 (텍스트 파싱 또는 LLM 판단 필요)
    # addAplyQlfcCndCn → 추가 신청 자격 조건
    # ptcpPrpTrgtCn   → 참여 제한 대상

    return "YES"


def main():

    users_path = os.path.join(BASE_DIR, "dummy_data.json")
    policy_path = os.path.join(BASE_DIR, "ontongAPI.json")

    with open(users_path, encoding="utf-8") as f:
        users = json.load(f)

    with open(policy_path, encoding="utf-8") as f:
        policy_data = json.load(f)

    # 실제 공고 리스트
    policies = policy_data["result"]["youthPolicyList"]

    results = []

    # 사용자 × 공고
    for user in users:
        for policy in policies:

            label = check_eligibility(user, policy)

            results.append({
                "user_id":     user["user_id"],
                "policy_id":   policy["plcyNo"],
                "policy_name": policy["plcyNm"],
                "label":       label
            })

    # Ground Truth 저장
    ground_truth_path = os.path.join(BASE_DIR, "ground_truth.csv")

    with open(
        ground_truth_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "user_id",
                "policy_id",
                "policy_name",
                "label"
            ]
        )

        writer.writeheader()
        writer.writerows(results)

    print("Ground Truth 생성 완료!")
    print(f"사용자 수  : {len(users)}")
    print(f"공고 수    : {len(policies)}")
    print(f"총 결과 수 : {len(results)}건")
    print(f"CSV 저장   : {ground_truth_path}")

    # 간단한 YES/NO 통계
    yes_count = sum(1 for r in results if r["label"] == "YES")
    no_count  = sum(1 for r in results if r["label"] == "NO")
    print(f"\nYES : {yes_count}건 ({yes_count/len(results)*100:.1f}%)")
    print(f"NO  : {no_count}건 ({no_count/len(results)*100:.1f}%)")


if __name__ == "__main__":
    main()
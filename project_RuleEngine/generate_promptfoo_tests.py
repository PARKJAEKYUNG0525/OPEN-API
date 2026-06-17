import os
import json
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 파일 경로
users_path = os.path.join(BASE_DIR, "dummy_data.json")
policy_path = os.path.join(BASE_DIR, "ontongAPI.json")
ground_truth_path = os.path.join(BASE_DIR, "ground_truth.csv")
output_path = os.path.join(BASE_DIR, "promptfoo_tests.csv")


def main():
    # 사용자 불러오기
    with open(users_path, encoding="utf-8") as f:
        users = json.load(f)

    user_map = {
        user["user_id"]: user
        for user in users
    }

    # 공고 불러오기
    with open(policy_path, encoding="utf-8") as f:
        policy_data = json.load(f)

    policies = policy_data["result"]["youthPolicyList"]

    policy_map = {
        policy["plcyNo"]: policy
        for policy in policies
    }

    rows = []

    # Rule Engine 정답 불러오기
    with open(ground_truth_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            user_id = int(row["user_id"])
            policy_id = row["policy_id"]
            expected = row["label"]

            user = user_map.get(user_id)
            policy = policy_map.get(policy_id)

            if user is None or policy is None:
                continue

            # Promptfoo에 들어갈 질문(input)
            input_text = f"""
사용자 정보
- 나이: {user['age']}세
- 성별: {user['gender']}
- 거주지역: {user['region']} {user['district']}
- 학력: {user['education']}
- 취업상태: {user['employment_status']}
- 월소득: {user['monthly_income']}원
- 결혼상태: {user['marital_status']}
- 장애여부: {'예' if user['disability'] else '아니오'}
- 군복무: {user['military_status']}

공고 정보
- 공고명: {policy['plcyNm']}
- 공고 설명: {policy['plcyExplnCn']}
- 지원 연령: {policy['sprtTrgtMinAge']}~{policy['sprtTrgtMaxAge']}세
- 추가 자격조건: {policy['addAplyQlfcCndCn']}
- 소득 조건: {policy['earnEtcCn']}

위 사용자의 해당 공고 지원 가능 여부를
YES 또는 NO로만 답하시오.
""".strip()

            rows.append({
                "input": input_text,
                "expected": expected
            })

    # Promptfoo용 CSV 저장
    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["input", "expected"]
        )

        writer.writeheader()
        writer.writerows(rows)

    print("promptfoo_tests.csv 생성 완료!")
    print(f"총 테스트 수: {len(rows)}")
    print(f"저장 위치: {output_path}")


if __name__ == "__main__":
    main()
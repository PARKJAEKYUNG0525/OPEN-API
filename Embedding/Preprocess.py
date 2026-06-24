import json
import random
from sklearn.model_selection import train_test_split

# ── 설정 ──────────────────────────────────────────────────
LABELS = ["annual_income", "is_business_owner", "household_income", "household_size"]
RANDOM_SEED = 42

# ── 데이터 로드 ───────────────────────────────────────────
with open("../성능평가/ontongAPI_2600.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("../INCOME_test/notice_Truth_2600.json", "r", encoding="utf-8") as f:
    truth = json.load(f)

policies     = data["result"]["youthPolicyList"]
truth_dict   = {item["plcyNo"]: item["required_fields"] for item in truth}
policy_dict  = {p["plcyNo"]: p for p in policies}

print(f"공고문 수 : {len(policies)}")
print(f"정답 수   : {len(truth)}")

# ── 텍스트 빌더 ───────────────────────────────────────────
def build_text(policy: dict) -> str:
    parts = [
        policy.get("earnEtcCn", ""),
        policy.get("addAplyQlfcCndCn", ""),
        policy.get("plcySprtCn", ""),
        policy.get("ptcpPrpTrgtCn", ""),
        policy.get("etcMttrCn", ""),
    ]
    return " ".join(p.strip() for p in parts if p.strip())

# ── 데이터셋 구성 ─────────────────────────────────────────
dataset = []

for plcy_no, required_fields in truth_dict.items():
    policy = policy_dict.get(plcy_no)
    if not policy:
        continue

    text = build_text(policy)
    if not text:
        continue

    # annual_sales 제외, 나머지 4개 라벨만 멀티라벨 벡터로 변환
    # [annual_income, is_business_owner, household_income, household_size]
    label_vector = [1 if label in required_fields else 0 for label in LABELS]

    dataset.append({
        "plcyNo": plcy_no,
        "text": text,
        "labels": label_vector,
        "required_fields": [f for f in required_fields if f in LABELS],
    })

print(f"\n전처리된 데이터 수 : {len(dataset)}개")

# ── 라벨 분포 확인 ────────────────────────────────────────
print("\n라벨 분포:")
for i, label in enumerate(LABELS):
    count = sum(1 for d in dataset if d["labels"][i] == 1)
    print(f"  {label:25s} : {count}개")

empty_count = sum(1 for d in dataset if sum(d["labels"]) == 0)
print(f"\n빈 라벨 수 : {empty_count}개")
print(f"라벨 있는 수 : {len(dataset) - empty_count}개")

# ── 학습/검증 분리 (80/20) ────────────────────────────────
train_data, val_data = train_test_split(
    dataset,
    test_size=0.2,
    random_state=RANDOM_SEED,
)

print(f"\n학습 데이터 : {len(train_data)}개")
print(f"검증 데이터 : {len(val_data)}개")

# ── 저장 ──────────────────────────────────────────────────
with open("train_data.json", "w", encoding="utf-8") as f:
    json.dump(train_data, f, ensure_ascii=False, indent=2)

with open("val_data.json", "w", encoding="utf-8") as f:
    json.dump(val_data, f, ensure_ascii=False, indent=2)

print("\ntrain_data.json 생성 완료")
print("val_data.json 생성 완료")

# ── 샘플 확인 ─────────────────────────────────────────────
print("\n샘플 확인:")
for d in dataset[:3]:
    print(f"  plcyNo : {d['plcyNo']}")
    print(f"  labels : {d['labels']} → {d['required_fields']}")
    print(f"  text   : {d['text'][:80]}...")
    print()
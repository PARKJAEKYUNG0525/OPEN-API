# check_data.py
import json

with open("../성능평가/ontongAPI_2600.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("../INCOME_test/notice_Truth_2600.json", "r", encoding="utf-8") as f:
    truth = json.load(f)

policies = data["result"]["youthPolicyList"]

print(f"공고문 수: {len(policies)}")
print(f"정답 수: {len(truth)}")
print(f"\n공고문 샘플 키: {list(policies[0].keys())[:5]}")
print(f"\n정답 샘플: {truth[0]}")

# 라벨 분포 확인
from collections import Counter
all_labels = []
for item in truth:
    all_labels.extend(item["required_fields"])

print(f"\n라벨 분포:")
for label, count in Counter(all_labels).items():
    print(f"  {label}: {count}개")

empty = sum(1 for item in truth if item["required_fields"] == [])
print(f"\n빈 required_fields 수: {empty}개")
print(f"라벨 있는 수: {500 - empty}개")
import json
import os
import glob

# ── 정답 로드 ─────────────────────────────────────────────
with open("notice_Truth.json", "r", encoding="utf-8") as f:
    truth_list = json.load(f)

truth = {item["plcyNo"]: sorted(item["required_fields"]) for item in truth_list}

# ── 비교할 예측 파일들 ────────────────────────────────────
pred_files = {
    "mistral-large-2512"  : "prediction_Watson_mistral_large_2512.json",
    "mistral-medium-2505" : "prediction_Watson_mistralai_mistral_medium_2505.json",
    "mistral-small-3-1"   : "prediction_Watson_mistralai_mistral_small_3_1_24b_instruct_2503.json",
}

print(f"{'모델':<25} {'Exact':>6} {'Prec':>6} {'Rec':>6} {'F1':>6}")
print("-" * 55)

for model_name, pred_file in pred_files.items():
    if not os.path.exists(pred_file):
        print(f"{model_name:<25}  파일 없음: {pred_file}")
        continue

    with open(pred_file, "r", encoding="utf-8") as f:
        pred_list = json.load(f)

    pred = {item["plcyNo"]: sorted(item.get("required_fields", [])) for item in pred_list}

    exact = 0
    total_prec, total_rec, total_f1 = 0.0, 0.0, 0.0
    wrong_cases = []
    n = 0

    for plcy_no, true_fields in truth.items():
        pred_fields = pred.get(plcy_no, [])
        n += 1

        # Exact match
        if pred_fields == true_fields:
            exact += 1

        # Precision / Recall / F1
        true_set = set(true_fields)
        pred_set = set(pred_fields)

        if len(pred_set) == 0 and len(true_set) == 0:
            prec = rec = f1 = 1.0
        else:
            prec = len(true_set & pred_set) / len(pred_set) if pred_set else 0.0
            rec  = len(true_set & pred_set) / len(true_set) if true_set else 1.0
            f1   = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        total_prec += prec
        total_rec  += rec
        total_f1   += f1

        if pred_fields != true_fields:
            wrong_cases.append({
                "plcyNo": plcy_no,
                "정답"  : true_fields,
                "예측"  : pred_fields,
                "과잉(FP)": sorted(pred_set - true_set),
                "누락(FN)": sorted(true_set - pred_set),
            })

    avg_prec = total_prec / n
    avg_rec  = total_rec  / n
    avg_f1   = total_f1   / n

    print(f"{model_name:<25} {exact}/{n}  {avg_prec:>5.3f}  {avg_rec:>5.3f}  {avg_f1:>5.3f}")

    if wrong_cases:
        print(f"\n  ── 틀린 케이스 ({len(wrong_cases)}개) [{model_name}] ──")
        for c in wrong_cases:
            print(f"  plcyNo : {c['plcyNo']}")
            print(f"  정답   : {c['정답']}")
            print(f"  예측   : {c['예측']}")
            if c["과잉(FP)"]: print(f"  과잉(FP): {c['과잉(FP)']}")
            if c["누락(FN)"]: print(f"  누락(FN): {c['누락(FN)']}")
            print()
    print()
import json

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_avg_elapsed(pred_list):
    """JSON에서 평균 소요시간 계산"""
    times = [item.get("elapsed_sec", 0) for item in pred_list if "elapsed_sec" in item]
    return sum(times) / len(times) if times else 0

# def evaluate(truth_list, pred_list, label="", field_key="required_fields"):
#     truth_dict = {item["plcyNo"]: set(item["required_fields"]) for item in truth_list}
#     pred_dict  = {item["plcyNo"]: set(item.get(field_key, [])) for item in pred_list}

def evaluate(truth_list, pred_list, label="", field_key="required_fields"):
    pred_dict  = {item["plcyNo"]: set(item.get(field_key, [])) for item in pred_list}
    truth_dict = {item["plcyNo"]: set(item["required_fields"]) 
                  for item in truth_list if item["plcyNo"] in pred_dict}

    exact_match = 0
    total = len(truth_dict)
    tp_total = fp_total = fn_total = 0
    wrong_cases = []

    for plcy_no, truth_fields in truth_dict.items():
        pred_fields = pred_dict.get(plcy_no, set())

        tp = len(truth_fields & pred_fields)
        fp = len(pred_fields - truth_fields)
        fn = len(truth_fields - pred_fields)

        tp_total += tp
        fp_total += fp
        fn_total += fn

        if pred_fields == truth_fields:
            exact_match += 1
        else:
            wrong_cases.append({
                "plcyNo": plcy_no,
                "truth":  sorted(truth_fields),
                "pred":   sorted(pred_fields),
                "과잉(FP)": sorted(pred_fields - truth_fields),
                "누락(FN)": sorted(truth_fields - pred_fields),
            })

    precision = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0
    recall    = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    avg_time  = get_avg_elapsed(pred_list)

    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  전체 공고문 수  : {total}")
    print(f"  정확히 맞은 수  : {exact_match} / {total}  ({exact_match/total*100:.1f}%)")
    print(f"  Precision       : {precision:.3f}")
    print(f"  Recall          : {recall:.3f}")
    print(f"  F1 Score        : {f1:.3f}")
    if avg_time > 0:
        print(f"  공고 평균 시간  : {avg_time:.2f}초")

    if wrong_cases:
        print(f"\n  ── 틀린 케이스 ({len(wrong_cases)}개) ──")
        for c in wrong_cases:
            print(f"\n  plcyNo : {c['plcyNo']}")
            print(f"  정답   : {c['truth']}")
            print(f"  예측   : {c['pred']}")
            if c['과잉(FP)']: print(f"  과잉(FP): {c['과잉(FP)']}")
            if c['누락(FN)']: print(f"  누락(FN): {c['누락(FN)']}")

    return {
        "exact": exact_match, "total": total,
        "f1": f1, "precision": precision, "recall": recall,
        "avg_time": avg_time, "wrong": wrong_cases,
    }


# ── 로드 ──────────────────────────────────────────────────
truth            = load_json("notice_Truth.json")
pred_rule      = load_json("prediction_Ollama(rule).json")
pred_llm       = load_json("prediction_Ollama(LLM_only).json")
pred_watson      = load_json("prediction_Watson(llm_only).json")
pred_watson_rule = load_json("prediction_Watson(rule).json")

# ── 평가 ──────────────────────────────────────────────────
r1 = evaluate(truth, pred_rule, label="Rule+Ollama  (prediction_Ollama(rule).json)")
r2 = evaluate(truth, pred_llm,  label="LLM only  (prediction_Ollama(LLM_only).json)")
r3 = evaluate(truth, pred_watson,      label="LLM only (Watson)  (prediction_Watson(llm_only).json)")
r4 = evaluate(truth, pred_watson_rule, label="Rule+Watson  (prediction_Watson(rule).json)")


# ── 비교 요약 ──────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  비교 요약")
print(f"{'='*60}")
print(f"  {'':25s}  {'Exact':>8s}  {'Prec':>6s}  {'Rec':>6s}  {'F1':>6s}  {'평균시간':>8s}")
print(f"  {'LLM only (Ollama)':25s}  {r2['exact']:>4}/{r2['total']}  {r2['precision']:.3f}  {r2['recall']:.3f}  {r2['f1']:.3f}  {r2['avg_time']:>6.2f}초")
print(f"  {'Rule+Ollama':25s}  {r1['exact']:>4}/{r1['total']}  {r1['precision']:.3f}  {r1['recall']:.3f}  {r1['f1']:.3f}  {r1['avg_time']:>6.2f}초")
print(f"  {'LLM only (Watson)':25s}  {r3['exact']:>4}/{r3['total']}  {r3['precision']:.3f}  {r3['recall']:.3f}  {r3['f1']:.3f}  {r3['avg_time']:>6.2f}초")
print(f"  {'Rule+Watson':25s}  {r4['exact']:>4}/{r4['total']}  {r4['precision']:.3f}  {r4['recall']:.3f}  {r4['f1']:.3f}  {r4['avg_time']:>6.2f}초")
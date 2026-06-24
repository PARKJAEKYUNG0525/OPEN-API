import json
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import f1_score, precision_score, recall_score
import time

# ── 설정 ──────────────────────────────────────────────────
LABELS     = ["annual_income", "is_business_owner", "household_income", "household_size"]
MAX_LEN    = 256
BATCH_SIZE = 16
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODELS = {
    "KoELECTRA"    : "koelectra_model",
    "TUNiB-Electra": "tunib_model",
    "Ko-SRoBERTa"  : "sroberta_model",
}

print(f"디바이스: {DEVICE}")

# ── 데이터셋 클래스 ───────────────────────────────────────
class PolicyDataset(Dataset):
    def __init__(self, data, tokenizer):
        self.data      = data
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        encoding = self.tokenizer(
            item["text"],
            max_length=MAX_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids":      encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels":         torch.tensor(item["labels"], dtype=torch.float),
        }

# ── 예측 함수 ─────────────────────────────────────────────
def predict(model, dataloader):
    model.eval()
    all_preds  = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids      = batch["input_ids"].to(DEVICE)
            attention_mask = batch["attention_mask"].to(DEVICE)
            labels         = batch["labels"].to(DEVICE)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits  = outputs.logits

            preds = (torch.sigmoid(logits) > 0.5).int().cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.int().cpu().numpy())

    return np.array(all_preds), np.array(all_labels)

# ── 검증 데이터 로드 ──────────────────────────────────────
with open("val_data.json", "r", encoding="utf-8") as f:
    val_data = json.load(f)

print(f"검증 데이터 : {len(val_data)}개\n")

# ── 모델별 평가 ───────────────────────────────────────────
summary = []

for model_name, model_path in MODELS.items():
    print(f"{'='*50}")
    print(f"  {model_name}")
    print(f"{'='*50}")

    start = time.time()

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model     = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.to(DEVICE)

    val_dataset = PolicyDataset(val_data, tokenizer)
    val_loader  = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    preds, labels = predict(model, val_loader)
    elapsed = time.time() - start

    precision = precision_score(labels, preds, average="micro", zero_division=0)
    recall    = recall_score(labels, preds, average="micro", zero_division=0)
    f1        = f1_score(labels, preds, average="micro", zero_division=0)

    # 라벨별 성능
    print(f"  전체 Precision : {precision:.3f}")
    print(f"  전체 Recall    : {recall:.3f}")
    print(f"  전체 F1        : {f1:.3f}")
    print(f"  소요 시간      : {elapsed:.2f}초")

    print(f"\n  라벨별 F1:")
    for i, label in enumerate(LABELS):
        label_f1 = f1_score(labels[:, i], preds[:, i], zero_division=0)
        print(f"    {label:25s} : {label_f1:.3f}")

    # 틀린 케이스
    wrong = []
    for idx, (pred, label) in enumerate(zip(preds, labels)):
        if not np.array_equal(pred, label):
            pred_fields  = [LABELS[i] for i in range(len(LABELS)) if pred[i] == 1]
            truth_fields = [LABELS[i] for i in range(len(LABELS)) if label[i] == 1]
            fp = [f for f in pred_fields  if f not in truth_fields]
            fn = [f for f in truth_fields if f not in pred_fields]
            wrong.append({
                "plcyNo": val_data[idx]["plcyNo"],
                "truth" : sorted(truth_fields),
                "pred"  : sorted(pred_fields),
                "과잉(FP)": sorted(fp),
                "누락(FN)": sorted(fn),
            })

    exact = len(val_data) - len(wrong)
    print(f"\n  정확히 맞은 수 : {exact} / {len(val_data)} ({exact/len(val_data)*100:.1f}%)")

    if wrong:
        print(f"\n  ── 틀린 케이스 ({len(wrong)}개) ──")
        for c in wrong[:5]:  # 최대 5개만 출력
            print(f"\n    plcyNo : {c['plcyNo']}")
            print(f"    정답   : {c['truth']}")
            print(f"    예측   : {c['pred']}")
            if c['과잉(FP)']: print(f"    과잉(FP): {c['과잉(FP)']}")
            if c['누락(FN)']: print(f"    누락(FN): {c['누락(FN)']}")
        if len(wrong) > 5:
            print(f"\n    ... 외 {len(wrong)-5}개")

    summary.append({
        "model"    : model_name,
        "exact"    : exact,
        "total"    : len(val_data),
        "precision": precision,
        "recall"   : recall,
        "f1"       : f1,
        "elapsed"  : elapsed,
    })

    # 결과 저장
    output_file = f"prediction_embedding_{model_name.replace('-', '_').replace(' ', '_')}.json"
    results = []
    for idx, (pred, label) in enumerate(zip(preds, labels)):
        pred_fields = [LABELS[i] for i in range(len(LABELS)) if pred[i] == 1]
        results.append({
            "plcyNo"         : val_data[idx]["plcyNo"],
            "required_fields": pred_fields,
        })
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  {output_file} 저장 완료")

# ── 최종 비교 요약 ────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  비교 요약")
print(f"{'='*65}")
print(f"  {'모델':20s}  {'Exact':>8s}  {'Prec':>6s}  {'Rec':>6s}  {'F1':>6s}  {'시간':>6s}")
for s in summary:
    print(f"  {s['model']:20s}  {s['exact']:>4}/{s['total']}  {s['precision']:.3f}  {s['recall']:.3f}  {s['f1']:.3f}  {s['elapsed']:>5.2f}초")
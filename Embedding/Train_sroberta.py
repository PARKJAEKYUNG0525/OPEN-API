import json
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.optim import AdamW
from sklearn.metrics import f1_score, precision_score, recall_score
import time

# ── 설정 ──────────────────────────────────────────────────
MODEL_NAME  = "jhgan/ko-sroberta-multitask"
LABELS      = ["annual_income", "is_business_owner", "household_income", "household_size"]
NUM_LABELS  = len(LABELS)
MAX_LEN     = 256
BATCH_SIZE  = 16
EPOCHS      = 5
LR          = 2e-5
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"모델   : {MODEL_NAME}")
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

# ── 평가 함수 ─────────────────────────────────────────────
def evaluate(model, dataloader):
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

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)

    precision = precision_score(all_labels, all_preds, average="micro", zero_division=0)
    recall    = recall_score(all_labels, all_preds, average="micro", zero_division=0)
    f1        = f1_score(all_labels, all_preds, average="micro", zero_division=0)

    return precision, recall, f1


# ── 데이터 로드 ───────────────────────────────────────────
with open("train_data.json", "r", encoding="utf-8") as f:
    train_data = json.load(f)

with open("val_data.json", "r", encoding="utf-8") as f:
    val_data = json.load(f)

print(f"\n학습 데이터 : {len(train_data)}개")
print(f"검증 데이터 : {len(val_data)}개")

# ── 토크나이저 & 모델 로드 ────────────────────────────────
print("\n모델 로딩 중...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model     = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=NUM_LABELS,
    problem_type="multi_label_classification",
)
model.to(DEVICE)

# ── 데이터로더 ────────────────────────────────────────────
train_dataset = PolicyDataset(train_data, tokenizer)
val_dataset   = PolicyDataset(val_data,   tokenizer)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)

# ── 옵티마이저 ────────────────────────────────────────────
optimizer = AdamW(model.parameters(), lr=LR)

# ── 학습 루프 ─────────────────────────────────────────────
print("\n학습 시작!")
total_start = time.time()
best_f1     = 0

for epoch in range(EPOCHS):
    model.train()
    total_loss  = 0
    epoch_start = time.time()

    for batch in train_loader:
        input_ids      = batch["input_ids"].to(DEVICE)
        attention_mask = batch["attention_mask"].to(DEVICE)
        labels         = batch["labels"].to(DEVICE)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss    = outputs.loss
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    avg_loss = total_loss / len(train_loader)
    precision, recall, f1 = evaluate(model, val_loader)
    epoch_elapsed = time.time() - epoch_start

    print(f"\n[Epoch {epoch+1}/{EPOCHS}]  ⏱ {epoch_elapsed:.1f}초")
    print(f"  Loss      : {avg_loss:.4f}")
    print(f"  Precision : {precision:.3f}")
    print(f"  Recall    : {recall:.3f}")
    print(f"  F1        : {f1:.3f}")

    if f1 > best_f1:
        best_f1 = f1
        model.save_pretrained("sroberta_model")
        tokenizer.save_pretrained("sroberta_model")
        print(f"  ✅ 최고 F1 갱신 → 모델 저장")

total_elapsed = time.time() - total_start
print(f"\n{'='*50}")
print(f"  학습 완료!")
print(f"  최고 F1     : {best_f1:.3f}")
print(f"  총 소요시간 : {total_elapsed:.1f}초")
print(f"{'='*50}")
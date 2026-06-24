import json

with open("../성능평가/ontongAPI_50.json", "r", encoding="utf-8") as f:
    data = json.load(f)

target = ["20260618005400213241", "20260614005400213232"]

for p in data["result"]["youthPolicyList"]:
    if p["plcyNo"] in target:
        search_text = "\n".join([
            p.get("earnEtcCn", ""),
            p.get("addAplyQlfcCndCn", ""),
            p.get("plcySprtCn", ""),
            p.get("ptcpPrpTrgtCn", ""),
            p.get("plcyExplnCn", ""),
        ])
        print(f"\n{p['plcyNo']}")
        print(f"search_text:\n{search_text}")
        print(f"'매출액' in text: {'매출액' in search_text}")
        print(f"'연매출' in text: {'연매출' in search_text}")
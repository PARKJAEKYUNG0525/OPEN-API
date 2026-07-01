import json
import sys
from pathlib import Path

CACHE_PATH = Path(r"C:\OPEN-API\Calendar_Test\ai_schedule_cache.json")


def main():
    if len(sys.argv) < 2:
        print("사용법: python clear_cache_entry.py <plcyNo> [plcyNo2 ...]")
        print("예시:   python clear_cache_entry.py 20260605005400113228")
        return

    if not CACHE_PATH.exists():
        print(f"캐시 파일이 없습니다: {CACHE_PATH}")
        return

    data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    removed = []
    for plcy_no in sys.argv[1:]:
        if plcy_no in data:
            del data[plcy_no]
            removed.append(plcy_no)

    CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"삭제됨: {removed if removed else '(해당 키 없음)'}")
    print(f"남은 캐시 항목 수: {len(data)}")


if __name__ == "__main__":
    main()
import calendar as cal_module
import json
from datetime import date, datetime
from html import escape
from pathlib import Path

BOOKMARK_PATH = Path(r"C:\OPEN-API\Calendar_Test\bookmarks.json")
AI_CACHE_PATH = Path(r"C:\OPEN-API\Calendar_Test\ai_schedule_cache.json")

# 공고문별 고유 색상 팔레트 (순환 배정)
COLOR_PALETTE = [
    "#e24b4a",  # red
    "#3b82f6",  # blue
    "#8b5cf6",  # purple
    "#10b981",  # green
    "#f59e0b",  # amber
    "#ec4899",  # pink
]


def load_bookmarks() -> dict:
    """plcyNo -> 정책 dict 형태로 저장된 즐겨찾기 데이터를 불러온다"""
    if not BOOKMARK_PATH.exists():
        return {}
    return json.loads(BOOKMARK_PATH.read_text(encoding="utf-8"))


def save_bookmarks(bookmarks: dict) -> None:
    BOOKMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOOKMARK_PATH.write_text(
        json.dumps(bookmarks, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def toggle_bookmark(policy: dict) -> bool:
    """즐겨찾기 토글. 추가되면 True, 해제되면 False 반환"""
    bookmarks = load_bookmarks()
    plcy_no = policy.get("plcyNo")

    if plcy_no in bookmarks:
        del bookmarks[plcy_no]
        save_bookmarks(bookmarks)
        return False

    bookmarks[plcy_no] = policy
    save_bookmarks(bookmarks)
    return True


def load_ai_cache() -> dict:
    if not AI_CACHE_PATH.exists():
        return {}
    return json.loads(AI_CACHE_PATH.read_text(encoding="utf-8"))


def parse_period(aply_ymd: str):
    """'20260622 ~ 20261231' 형식에서 (시작일, 마감일) 파싱. 형식이 없거나 깨졌으면 (None, None)"""
    if not aply_ymd or "~" not in aply_ymd:
        return None, None
    parts = aply_ymd.split("~")
    if len(parts) != 2:
        return None, None
    try:
        start = datetime.strptime(parts[0].strip(), "%Y%m%d").date()
        end = datetime.strptime(parts[1].strip(), "%Y%m%d").date()
        return start, end
    except ValueError:
        return None, None


def parse_event_date(date_str: str):
    """AI 추출 결과의 date 필드를 파싱. 'YYYY-MM-DD'면 (date, True),
    'YYYY-MM'(일자 모름)이면 (그달 1일, False), 둘 다 실패하면 (None, False)"""
    if not date_str:
        return None, False
    try:
        if len(date_str) == 10:
            return datetime.strptime(date_str, "%Y-%m-%d").date(), True
        if len(date_str) == 7:
            return datetime.strptime(date_str + "-01", "%Y-%m-%d").date(), False
    except ValueError:
        pass
    return None, False


def build_events(policy: dict, ai_cache: dict) -> list:
    """정책 하나의 모든 일정을 통합. 각 항목:
    {"type": str, "date": date|None, "exact": bool, "raw_text": str|None}"""
    events = []

    start, end = parse_period(policy.get("aplyYmd"))
    if start:
        events.append({"type": "신청시작", "date": start, "exact": True, "raw_text": None})
    if end:
        events.append({"type": "신청마감", "date": end, "exact": True, "raw_text": None})

    ai_events = ai_cache.get(policy.get("plcyNo"), [])
    if isinstance(ai_events, list):  # {"error": ...} 형태(추출 실패)는 dict라서 자동으로 걸러짐
        for e in ai_events:
            d, exact = parse_event_date(e.get("date"))
            if d:
                events.append({
                    "type": e.get("type") or "일정",
                    "date": d,
                    "exact": exact,
                    "raw_text": e.get("raw_text"),
                })

    return events


def calc_dday(deadline: date) -> str:
    delta = (deadline - date.today()).days
    if delta < 0:
        return "마감"
    if delta == 0:
        return "D-DAY"
    return f"D-{delta}"


def shift_month(year: int, month: int, delta: int) -> tuple:
    m = month - 1 + delta
    return year + m // 12, m % 12 + 1


def render_calendar(year: int, month: int, dots_by_day: dict) -> str:
    c = cal_module.Calendar(firstweekday=6)  # 일요일 시작
    weeks = c.monthdayscalendar(year, month)
    day_labels = ["일", "월", "화", "수", "목", "금", "토"]

    header = "".join(f'<div class="dow">{d}</div>' for d in day_labels)

    rows = []
    for week in weeks:
        cells = []
        for day in week:
            if day == 0:
                cells.append('<div class="day empty"></div>')
                continue
            dots = dots_by_day.get(day, [])
            dot_html = ""
            for color, label in dots:
                dot_html += f'<span class="dot" style="background:{color}" title="{escape(label)}"></span>'
            cells.append(
                f'<div class="day"><span class="num">{day}</span>'
                f'<div class="dots">{dot_html}</div></div>'
            )
        rows.append(f'<div class="week">{"".join(cells)}</div>')

    py, pm = shift_month(year, month, -1)
    ny, nm = shift_month(year, month, 1)

    return f"""
    <div class="cal-head">
      <a class="cal-nav" href="/bookmarks?year={py}&month={pm}">‹</a>
      <span class="cal-title">{year}년 {month}월</span>
      <a class="cal-nav" href="/bookmarks?year={ny}&month={nm}">›</a>
    </div>
    <div class="dow-row">{header}</div>
    {''.join(rows)}
    """


def render_bookmark_page(year: int = None, month: int = None) -> str:
    today = date.today()
    year = year or today.year
    month = month or today.month

    bookmarks = load_bookmarks()
    items = list(bookmarks.values())
    ai_cache = load_ai_cache()

    # 정책별 고유 색상 + 통합 이벤트 리스트 (인덱스 기준으로 색 고정 배정)
    colored_items = []
    for i, p in enumerate(items):
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
        events = build_events(p, ai_cache)
        colored_items.append((p, color, events))

    # 이번 달 + 일자(day)까지 정확한 이벤트만 캘린더 점으로 표시 (같은 공고문 = 같은 색)
    dots_by_day = {}
    for p, color, events in colored_items:
        name = p.get("plcyNm", "")
        for ev in events:
            d = ev["date"]
            if ev["exact"] and d.year == year and d.month == month:
                label = f"{name} · {ev['type']}"
                dots_by_day.setdefault(d.day, []).append((color, label))

    legend = "".join(
        f'<span class="legend-item"><span class="dot" style="background:{color}"></span>{escape(p.get("plcyNm", ""))}</span>'
        for p, color, events in colored_items
    )

    cards = []
    for p, color, events in colored_items:
        plcy_no = escape(p.get("plcyNo", ""))
        name = escape(p.get("plcyNm", "(이름 없음)"))
        org = escape(p.get("sprvsnInstCdNm") or p.get("operInstCdNm") or "-")

        deadline = next((e["date"] for e in events if e["type"] == "신청마감"), None)
        dday_label = calc_dday(deadline) if deadline else "상시/미정"

        events_sorted = sorted(events, key=lambda e: e["date"])
        event_rows = []
        for ev in events_sorted:
            if ev["exact"]:
                date_label = f"{ev['date'].month}/{ev['date'].day}"
            else:
                date_label = f"{ev['date'].year}년 {ev['date'].month}월 (일자 미상)"
            raw = f'<span class="raw">"{escape(ev["raw_text"])}"</span>' if ev["raw_text"] else ""
            event_rows.append(
                f'<div class="event-row">'
                f'<span class="event-type">{escape(ev["type"])}</span>'
                f'<span class="event-date">{date_label}</span>{raw}'
                f"</div>"
            )
        events_html = "".join(event_rows) or '<p class="no-events">추출된 일정 없음</p>'

        cards.append(f"""
        <div class="card">
          <div class="card-head">
            <span class="dot-lg" style="background:{color}"></span>
            <h2>{name}</h2>
            <span class="dday">{escape(dday_label)}</span>
          </div>
          <p class="meta">{org}</p>
          <div class="events">{events_html}</div>
          <form method="post" action="/bookmark/{plcy_no}">
            <button type="submit" class="bookmarked">즐겨찾기 해제</button>
          </form>
        </div>""")

    cal_html = render_calendar(year, month, dots_by_day)
    list_html = "".join(cards) if cards else '<p class="empty">즐겨찾기한 공고문이 없습니다.</p>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>내 지원금 캘린더 ({len(items)}건)</title>
<style>
  body {{ font-family: -apple-system, "Malgun Gothic", sans-serif; background: #f5f5f4; margin: 0; padding: 24px; }}
  .nav {{ margin-bottom: 16px; }}
  .nav a {{ font-size: 13px; color: #555; text-decoration: none; margin-right: 12px; }}
  .nav a.active {{ color: #111; font-weight: 600; }}
  h1 {{ font-size: 18px; font-weight: 600; margin: 0 0 16px; }}

  .cal-head {{ display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 8px; }}
  .cal-title {{ font-size: 15px; font-weight: 600; }}
  .cal-nav {{ text-decoration: none; color: #555; font-size: 16px; padding: 0 6px; }}
  .dow-row, .week {{ display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; }}
  .dow {{ font-size: 11px; color: #999; padding: 6px 0; }}
  .day {{ display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 6px 0; font-size: 12px; }}
  .day.empty {{ visibility: hidden; }}
  .dots {{ display: flex; gap: 2px; height: 6px; justify-content: center; flex-wrap: wrap; }}
  .dot {{ width: 5px; height: 5px; border-radius: 50%; display: inline-block; }}
  .dot-caption {{ text-align: center; font-size: 11px; color: #999; margin-top: 4px; }}
  .dot-lg {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}

  .legend {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 14px 0 20px; padding-top: 10px; border-top: 1px solid #e5e5e5; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 12px; color: #555; }}

  .card {{ background: #fff; border: 1px solid #e5e5e5; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }}
  .card-head {{ display: flex; align-items: center; gap: 8px; }}
  .card-head h2 {{ font-size: 15px; margin: 0; flex: 1; }}
  .dday {{ font-size: 11px; font-weight: 600; background: #eee; color: #555; padding: 2px 8px; border-radius: 5px; white-space: nowrap; }}
  .meta {{ font-size: 12px; color: #666; margin: 4px 0 8px 18px; }}
  .events {{ margin: 0 0 10px 18px; display: flex; flex-direction: column; gap: 4px; }}
  .event-row {{ font-size: 12px; color: #444; display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }}
  .event-type {{ font-weight: 600; min-width: 56px; }}
  .event-date {{ color: #666; }}
  .raw {{ color: #999; font-size: 11px; }}
  .no-events {{ font-size: 12px; color: #aaa; margin: 0; }}
  button {{ border: none; border-radius: 6px; padding: 6px 12px; font-size: 13px; cursor: pointer; background: #eee; }}
  button.bookmarked {{ background: #fde68a; color: #92400e; }}
  .empty {{ color: #888; font-size: 14px; }}
</style>
</head>
<body>
  <div class="nav">
    <a href="/">전체 공고문</a>
    <a href="/bookmarks" class="active">즐겨찾기 ({len(items)})</a>
  </div>
  <h1>내 지원금 캘린더</h1>
  {cal_html}
  <p class="dot-caption">점에 마우스를 올리면 정책명·일정 종류가 표시됩니다 (일자 미상인 일정은 점 표시 없이 목록에서만 확인 가능)</p>
  <div class="legend">{legend}</div>
  <h1>즐겨찾기 일정 {len(items)}</h1>
  {list_html}
</body>
</html>"""
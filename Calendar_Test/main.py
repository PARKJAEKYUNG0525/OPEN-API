import json
import webbrowser
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

import Bookmark

JSON_PATH = Path(r"C:\OPEN-API\성능평가\ontongAPI.json")
PORT = 8000


def find_list_of_dicts(data):
    """JSON 구조 안에서 정책 객체가 담긴 리스트를 재귀적으로 탐색 (중첩 깊이/키 이름 무관)"""
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return data
        return None
    if isinstance(data, dict):
        for value in data.values():
            found = find_list_of_dicts(value)
            if found is not None:
                return found
    return None


def load_policies(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    policies = find_list_of_dicts(data)
    if policies is None:
        keys = list(data.keys()) if isinstance(data, dict) else type(data)
        raise ValueError(f"정책 리스트를 찾지 못했습니다. 최상위 구조: {keys}")
    return policies


def render_main_page(policies: list) -> str:
    bookmarks = Bookmark.load_bookmarks()

    cards = []
    for p in policies:
        plcy_no = escape(p.get("plcyNo", ""))
        name = escape(p.get("plcyNm", "(이름 없음)"))
        org = escape(p.get("sprvsnInstCdNm") or p.get("operInstCdNm") or "-")
        period = escape(p.get("aplyYmd") or "-")
        category = escape(p.get("lclsfNm", "-"))
        age = f"{p.get('sprtTrgtMinAge', '?')}세 ~ {p.get('sprtTrgtMaxAge', '?')}세"
        desc = escape(p.get("plcyExplnCn", ""))

        is_bookmarked = p.get("plcyNo") in bookmarks
        btn_label = "★ 즐겨찾기됨" if is_bookmarked else "☆ 즐겨찾기"
        btn_class = "bookmarked" if is_bookmarked else ""

        cards.append(f"""
        <div class="card">
          <span class="tag">{category}</span>
          <h2>{name}</h2>
          <p class="meta">{org} · 신청기간 {period} · {age}</p>
          <p class="desc">{desc}</p>
          <form method="post" action="/bookmark/{plcy_no}">
            <button type="submit" class="{btn_class}">{btn_label}</button>
          </form>
        </div>""")

    bookmark_count = len(bookmarks)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>공고문 전체보기 ({len(policies)}건)</title>
<style>
  body {{ font-family: -apple-system, "Malgun Gothic", sans-serif; background: #f5f5f4; margin: 0; padding: 24px; }}
  .nav {{ margin-bottom: 16px; }}
  .nav a {{ font-size: 13px; color: #555; text-decoration: none; margin-right: 12px; }}
  .nav a.active {{ color: #111; font-weight: 600; }}
  h1 {{ font-size: 18px; font-weight: 600; margin: 0 0 16px; }}
  .card {{ background: #fff; border: 1px solid #e5e5e5; border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; }}
  .tag {{ display: inline-block; font-size: 11px; color: #555; background: #eee; padding: 2px 8px; border-radius: 4px; margin-bottom: 6px; }}
  h2 {{ font-size: 16px; margin: 4px 0; }}
  .meta {{ font-size: 13px; color: #666; margin: 4px 0; }}
  .desc {{ font-size: 13px; color: #333; line-height: 1.5; margin: 8px 0 12px; }}
  button {{ border: none; border-radius: 6px; padding: 6px 12px; font-size: 13px; cursor: pointer; background: #eee; color: #333; }}
  button.bookmarked {{ background: #fde68a; color: #92400e; }}
</style>
</head>
<body>
  <div class="nav">
    <a href="/" class="active">전체 공고문</a>
    <a href="/bookmarks">즐겨찾기 ({bookmark_count})</a>
  </div>
  <h1>공고문 전체보기 ({len(policies)}건)</h1>
  {''.join(cards)}
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            policies = load_policies(JSON_PATH)
            html = render_main_page(policies)
        elif path == "/bookmarks":
            year = int(query["year"][0]) if "year" in query else None
            month = int(query["month"][0]) if "month" in query else None
            html = Bookmark.render_bookmark_page(year, month)
        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        if self.path.startswith("/bookmark/"):
            plcy_no = unquote(self.path.removeprefix("/bookmark/"))
            policies = load_policies(JSON_PATH)
            policy = next((p for p in policies if p.get("plcyNo") == plcy_no), None)

            if policy:
                Bookmark.toggle_bookmark(policy)

            # 요청을 보낸 페이지로 되돌아가기
            referer = self.headers.get("Referer", "/")
            self.send_response(303)
            self.send_header("Location", referer)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # 콘솔에 매 요청 로그 안 찍히게 조용히 처리


def main():
    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"서버 실행 중: {url}  (종료하려면 Ctrl+C)")
    webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
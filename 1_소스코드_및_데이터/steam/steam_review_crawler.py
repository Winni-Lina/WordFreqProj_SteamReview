

import os
import re
import sys
import json
import time
import html
import signal

import requests

# ============================================================
#                       설정 (CONFIG)
#   여기 값만 바꿔서 사용하세요.
# ============================================================
STEAM_API_KEY = ""                       # Steam Web API 키 (작성자 닉네임 변환용, 없어도 됨)
# 조회할 주제(장르) 목록. 라운드 로빈으로 번갈아가며 모두 수집한다.
# Steam 스토어 공식 장르만 모아둠. 필요 없는 줄은 지우세요.
TOPICS = [
    "action",                 # 액션
    "adventure",              # 어드벤처
    "casual",                 # 캐주얼
    "indie",                  # 인디
    "massively multiplayer",  # 대규모 멀티플레이어(MMO)
    "racing",                 # 레이싱
    "rpg",                    # 롤플레잉
    "simulation",             # 시뮬레이션
    "sports",                 # 스포츠
    "strategy",               # 전략
]
OUTPUT_DIR = r"C:\Users\user\Desktop\WebCrawling\Steam_WebCrawler\output"
OUTPUT_DIR = r"C:\Users\user\Desktop\WebCrawling\Steam_WebCrawler\output"

MAX_GAMES = 30                            # 주제당 수집할 최대 게임 수 (0 = 제한 없음)
BATCH_PER_TOPIC = 1                        # 한 번에 한 주제에서 처리할 게임 수.
                                          #   이 개수만큼 끝내면 다음 주제로 넘어가고,
                                          #   모든 주제를 돈 뒤 다시 처음 주제로 돌아온다(라운드 로빈).
                                          #   1 = 게임 1개마다 주제 교대 / 큰 값 = 덜 교대
REVIEW_LANGUAGE = "all"                   # 리뷰 언어: "all", "koreana", "english" 등
RESOLVE_AUTHOR_NAMES = True               # True = 작성자를 닉네임으로 변환(API 키 필요)
TRANSLATE_TO_KOREAN = True                # True = 외국어 리뷰를 한국어로 번역(deep-translator 사용)
TRANSLATE_RETRY = 3                        # 번역 실패(구글 차단 등) 시 재시도 횟수
NUM_PER_PAGE = 100                        # 리뷰 한 페이지당 개수(최대 100)
REQUEST_DELAY = 1.0                       # 요청 사이 대기 시간(초) - 차단 방지
MAX_RETRY = 5                             # 요청 실패 시 재시도 횟수
STORE_CC = "kr"                           # 스토어 국가코드
STORE_LANG = "english"                    # 스토어 언어(게임 이름 기준). english = 원본 제목 / koreana = 한국어 현지화 제목
# ============================================================


REVIEWS_DIR = os.path.join(OUTPUT_DIR, "reviews")
PROGRESS_PATH = os.path.join(OUTPUT_DIR, "progress.json")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/123.0 Safari/537.36"
})

# 번역기 준비 (deep-translator). 설치되어 있지 않으면 번역은 건너뛴다.
_translator = None
if TRANSLATE_TO_KOREAN:
    try:
        from deep_translator import GoogleTranslator
        _translator = GoogleTranslator(source="auto", target="ko")
    except Exception:
        print("[!] deep-translator 가 설치되어 있지 않아 번역을 건너뜁니다.")
        print("    설치: pip install deep-translator")
        _translator = None

# 종료 요청 플래그 (Ctrl+C 시 안전하게 현재 페이지까지 저장 후 종료)
_stop_requested = False


def _handle_sigint(signum, frame):
    global _stop_requested
    _stop_requested = True
    print("\n[!] 종료 요청을 받았습니다. 현재 작업을 안전하게 마무리하고 종료합니다...")


signal.signal(signal.SIGINT, _handle_sigint)


# ------------------------------------------------------------
# 진행 상태(progress) 저장/로드
# ------------------------------------------------------------
def load_progress():
    if os.path.exists(PROGRESS_PATH):
        try:
            with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("[!] progress.json 을 읽지 못했습니다. 새로 시작합니다.")
    return {}


def save_progress(progress):
    tmp = PROGRESS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PROGRESS_PATH)  # 원자적 교체


def safe_folder_name(topic):
    """주제 문자열을 폴더 이름으로 안전하게 변환."""
    name = re.sub(r'[\\/:*?"<>|]+', "_", topic).strip().strip(".")
    return name or "topic"


# ------------------------------------------------------------
# 1) 주제로 게임 목록 가져오기 (스토어 검색)
# ------------------------------------------------------------
def get_games_by_topic(topic, max_games=0):
    """
    스토어 검색 결과에서 (appid, 게임이름) 목록을 추출한다.
    topic 은 검색어로 사용된다. (예: "roguelike", "horror", "소울라이크")
    """
    print(f"[*] '{topic}' 주제로 게임 목록을 검색합니다...")
    games = []
    seen = set()
    start = 0
    count = 100

    while True:
        params = {
            "term": topic,
            "start": start,
            "count": count,
            "infinite": 1,
            "l": STORE_LANG,
            "cc": STORE_CC,
        }
        try:
            r = session.get(
                "https://store.steampowered.com/search/results/",
                params=params, timeout=30,
            )
            data = r.json()
        except Exception as e:
            print(f"[!] 검색 요청 실패: {e}")
            break

        results_html = data.get("results_html", "") or ""
        total = data.get("total_count", 0)

        # <a ... data-ds-appid="570" ...> ... <span class="title">이름</span>
        matches = re.findall(
            r'data-ds-appid="([0-9,]+)".*?<span class="title">(.*?)</span>',
            results_html, re.S,
        )
        if not matches:
            break

        for appid_raw, title in matches:
            appid = appid_raw.split(",")[0].strip()
            if not appid or appid in seen:
                continue
            seen.add(appid)
            name = html.unescape(re.sub(r"<.*?>", "", title)).strip()
            games.append({"appid": appid, "name": name})
            if max_games and len(games) >= max_games:
                print(f"[*] 게임 {len(games)}개 수집(최대치 도달).")
                return games

        start += count
        if total and start >= total:
            break
        time.sleep(REQUEST_DELAY)

    print(f"[*] 게임 {len(games)}개를 찾았습니다.")
    return games


# ------------------------------------------------------------
# 2) 작성자 steamid -> 닉네임 변환 (Web API 키 사용)
# ------------------------------------------------------------
def resolve_persona_names(steamids):
    """steamids(list) -> {steamid: personaname} (최대 100개씩 배치)"""
    result = {}
    if not (RESOLVE_AUTHOR_NAMES and STEAM_API_KEY and steamids):
        return result

    unique = list({s for s in steamids if s})
    for i in range(0, len(unique), 100):
        batch = unique[i:i + 100]
        try:
            r = session.get(
                "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
                params={"key": STEAM_API_KEY, "steamids": ",".join(batch)},
                timeout=30,
            )
            players = r.json().get("response", {}).get("players", [])
            for p in players:
                result[p.get("steamid")] = p.get("personaname")
        except Exception:
            # 변환 실패 시 해당 배치는 steamid 그대로 사용
            pass
    return result


# ------------------------------------------------------------
# 2-1) 외국어 리뷰 -> 한국어 번역
# ------------------------------------------------------------
# 한국어로 간주해 번역을 건너뛸 Steam 언어 코드
_KOREAN_LANG_CODES = {"koreana", "korean", "ko"}
_MAX_CHUNK = 4500  # 구글 번역 1회 요청 글자 수 제한(약 5000) 대비


def _chunk_text(text, size=_MAX_CHUNK):
    """긴 텍스트를 줄바꿈 우선으로 잘라서 chunk 리스트로 반환."""
    chunks = []
    while len(text) > size:
        cut = text.rfind("\n", 0, size)
        if cut <= 0:
            cut = size
        chunks.append(text[:cut])
        text = text[cut:]
    if text:
        chunks.append(text)
    return chunks


def _translate_chunk(chunk):
    """청크 1개를 번역. 일시 실패(구글 차단 등) 시 잠깐 쉬었다 재시도."""
    for attempt in range(1, TRANSLATE_RETRY + 1):
        try:
            return _translator.translate(chunk) or chunk
        except Exception:
            if attempt < TRANSLATE_RETRY:
                time.sleep(REQUEST_DELAY * attempt)  # 점진적 대기 후 재시도
    return chunk  # 끝까지 실패하면 원문 유지(데이터 유실 방지)


def translate_to_korean(text, language):
    """
    외국어 리뷰 텍스트를 한국어로 번역해 반환한다.
    - 번역기가 없거나, 이미 한국어이거나, 빈 텍스트면 원문 그대로 반환.
    - 번역이 끝까지 실패하면 원문 그대로 반환(데이터 유실 방지).
    """
    if _translator is None or not text or not text.strip():
        return text
    if language and language.lower() in _KOREAN_LANG_CODES:
        return text
    return "".join(_translate_chunk(chunk) for chunk in _chunk_text(text))


# ------------------------------------------------------------
# 3) 리뷰 한 페이지 가져오기 (재시도 포함)
# ------------------------------------------------------------
def fetch_reviews_page(appid, cursor):
    params = {
        "json": 1,
        "filter": "recent",          # recent = cursor 페이지네이션이 끝까지 안정적
        "language": REVIEW_LANGUAGE,
        "cursor": cursor,
        "review_type": "all",
        "purchase_type": "all",
        "num_per_page": NUM_PER_PAGE,
        "filter_offtopic_activity": 0,  # 0 = 리뷰 폭격(off-topic)도 제외하지 않고 전부 수집
    }
    url = f"https://store.steampowered.com/appreviews/{appid}"

    for attempt in range(1, MAX_RETRY + 1):
        try:
            r = session.get(url, params=params, timeout=30)
            data = r.json()
            if data.get("success") == 1:
                return data
            print(f"    [!] success != 1 (시도 {attempt}/{MAX_RETRY})")
        except Exception as e:
            print(f"    [!] 리뷰 요청 실패: {e} (시도 {attempt}/{MAX_RETRY})")
        time.sleep(REQUEST_DELAY * attempt)  # 점진적 대기
    return None


# ------------------------------------------------------------
# 4) 한 게임의 모든 리뷰 수집
# ------------------------------------------------------------
def crawl_game_reviews(game, tstate, progress, out_path):
    """한 게임의 모든 리뷰를 out_path(주제별 파일)에 이어붙인다."""
    appid = game["appid"]
    name = game["name"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # 저장된 cursor 가 있으면 그 위치부터, 없으면 처음('*')부터
    cursor = tstate["cursors"].get(appid, "*")
    count = 0

    print(f"[*] 리뷰 수집 시작: {name} (appid={appid}) "
          f"{'(이어서)' if cursor != '*' else ''}")

    with open(out_path, "a", encoding="utf-8") as f:
        while True:
            if _stop_requested:
                return False  # 미완료 상태로 종료

            data = fetch_reviews_page(appid, cursor)
            if data is None:
                print(f"    [!] {name}: 페이지 수집 실패. 다음 실행 시 이어서 시도합니다.")
                return False

            # 첫 페이지에서 전체 리뷰 수를 확인(완전성 점검용)
            total_reviews = data.get("query_summary", {}).get("total_reviews")
            if cursor == "*" and total_reviews:
                print(f"    (이 게임 전체 리뷰 약 {total_reviews}개)")

            reviews = data.get("reviews", [])
            if not reviews:
                break  # 더 이상 리뷰 없음 -> 완료

            # 작성자 닉네임 변환
            steamids = [rv.get("author", {}).get("steamid") for rv in reviews]
            persona = resolve_persona_names(steamids)

            for rv in reviews:
                steamid = rv.get("author", {}).get("steamid", "")
                author = persona.get(steamid) or steamid
                review_text = translate_to_korean(
                    rv.get("review", ""), rv.get("language", "")
                )
                record = {
                    "게임 이름": name,
                    "작성자": author,
                    "리뷰 내용": review_text,
                    "평점": "추천" if rv.get("voted_up") else "비추천",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

            # 디스크에 확실히 기록
            f.flush()
            os.fsync(f.fileno())

            next_cursor = data.get("cursor")
            if not next_cursor or next_cursor == cursor:
                break  # 마지막 페이지

            # 리뷰를 먼저 쓴 뒤 cursor 를 저장(데이터 유실 방지)
            cursor = next_cursor
            tstate["cursors"][appid] = cursor
            save_progress(progress)

            print(f"    ... {count}개 수집됨")
            time.sleep(REQUEST_DELAY)

    # 완료 처리
    tstate["completed"].append(appid)
    tstate["cursors"].pop(appid, None)
    save_progress(progress)
    print(f"[완료] {name}: 총 {count}개 리뷰 저장 -> {out_path}")
    return True


# ------------------------------------------------------------
# 메인
# ------------------------------------------------------------
def ensure_topic_games(topic, progress):
    """주제의 게임 목록이 없으면 검색해서 캐시한다. 해당 주제 상태(tstate)를 반환."""
    tstate = progress["topics"].get(topic)
    if tstate and "games" in tstate:
        return tstate
    games = get_games_by_topic(topic, MAX_GAMES)
    if not games:
        print(f"[!] '{topic}': 검색된 게임이 없습니다. 건너뜁니다.")
    tstate = {"games": games, "completed": [], "cursors": {}}
    progress["topics"][topic] = tstate
    save_progress(progress)
    return tstate


def main():
    os.makedirs(REVIEWS_DIR, exist_ok=True)

    progress = load_progress()
    if "topics" not in progress:
        progress = {"topics": {}}

    print(f"[*] 수집할 주제: {', '.join(TOPICS)}")
    print(f"[*] 라운드 로빈: 주제당 {BATCH_PER_TOPIC}개씩 처리 후 다음 주제로 교대\n")

    # 라운드 로빈: 주제들을 번갈아 돌면서 BATCH_PER_TOPIC 개씩 처리.
    # 완료한 게임(completed)/멈춘 위치(cursors)는 progress.json 에 기록되므로,
    # 재실행 시 자동으로 멈춘 위치부터 이어서 수집한다.
    round_no = 0
    while not _stop_requested:
        round_no += 1
        any_work = False
        for topic in TOPICS:
            if _stop_requested:
                break
            tstate = ensure_topic_games(topic, progress)
            out_path = os.path.join(REVIEWS_DIR, safe_folder_name(topic) + ".jsonl")

            # 아직 완료하지 않은 게임들(멈춘 게임이 맨 앞에 옴)
            todo = [g for g in tstate["games"]
                    if g["appid"] not in tstate["completed"]]
            if not todo:
                continue  # 이 주제는 끝남

            any_work = True
            done = len(tstate["completed"])
            total = len(tstate["games"])
            print(f"\n===== [라운드 {round_no}] 주제: {topic} "
                  f"(진행 {done}/{total}, 이번에 {min(BATCH_PER_TOPIC, len(todo))}개) =====")
            for game in todo[:BATCH_PER_TOPIC]:
                if _stop_requested:
                    break
                crawl_game_reviews(game, tstate, progress, out_path)

        if not any_work:
            break  # 모든 주제의 모든 게임 완료

    if _stop_requested:
        print("\n[*] 중단되었습니다. 다시 실행하면 멈춘 주제/게임/페이지부터 이어서 수집합니다.")
    else:
        print("\n[*] 모든 주제의 리뷰 수집을 완료했습니다.")


if __name__ == "__main__":
    main()

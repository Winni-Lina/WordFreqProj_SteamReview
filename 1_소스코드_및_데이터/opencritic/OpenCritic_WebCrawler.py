import requests
import json
import os
import time
import re
from tqdm import tqdm

class OpenCriticFullFetcher:
    def __init__(self, api_key):
        self.base_url = "https://opencritic-api.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "opencritic-api.p.rapidapi.com"
        }
        self.data_file = "reviews_final_data.jsonl"
        self.progress_file = "processed_progress.json"
        self.error_log = "fetch_errors.log"

        self.PAGE_SIZE = 20  # OpenCritic API 한 페이지당 게임 수

    # ------------------------------------------------------------------ #
    #  유틸리티                                                             #
    # ------------------------------------------------------------------ #

    def _clean_text(self, text):
        if not text:
            return "내용 없음"
        return re.sub(r'\s+', ' ', text).strip()

    def _map_score_to_recommend(self, score):
        if isinstance(score, (int, float)):
            if score >= 75: return "강력 추천"
            if score >= 50: return "추천"
            return "평이함"
        return "정보 없음"

    def _safe_request(self, url, params=None):
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=self.headers, params=params, timeout=15)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 10))
                    print(f"\n[Rate Limit] {wait}초 대기 중...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == 2:
                    self._log_error(f"요청 실패 ({url}): {e}")
                time.sleep(2)
        return None

    def _log_error(self, message):
        with open(self.error_log, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    # ------------------------------------------------------------------ #
    #  진행 상황 저장 / 불러오기                                            #
    # ------------------------------------------------------------------ #

    def load_progress(self):
        """
        저장 형식:
        {
            "last_offset": 340,        # 게임 목록 수집 완료 offset
            "processed_ids": [1, 2, …] # 리뷰까지 수집 완료된 game_id 목록
        }
        """
        if os.path.exists(self.progress_file):
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["processed_ids"] = set(data.get("processed_ids", []))
                return data
        return {"last_offset": 0, "processed_ids": set()}

    def save_progress(self, last_offset, processed_ids):
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(
                {"last_offset": last_offset, "processed_ids": list(processed_ids)},
                f, ensure_ascii=False
            )

    # ------------------------------------------------------------------ #
    #  전체 게임 목록 수집 (페이지네이션)                                   #
    # ------------------------------------------------------------------ #

    def fetch_game_list_page(self, offset):
        """
        GET /game?skip={offset}&order=asc&sort=name
        반환: [{"id": 123, "name": "..."}, ...]  |  빈 리스트  |  None(에러)
        """
        data = self._safe_request(
            f"{self.base_url}/game",
            params={"skip": offset, "order": "asc", "sort": "name"}
        )
        if data is None:
            return None
        # API가 리스트 또는 {"results": [...]} 형태일 수 있어 양쪽 처리
        if isinstance(data, list):
            return data
        return data.get("results", [])

    # ------------------------------------------------------------------ #
    #  리뷰 수집                                                           #
    # ------------------------------------------------------------------ #

    def fetch_reviews(self, game_id, game_name):
        reviews = self._safe_request(f"{self.base_url}/reviews/game/{game_id}")
        if not reviews:
            return []

        result = []
        for r in reviews:
            result.append({
                "게임 이름": game_name,
                "작성자": r.get("authors", "익명 평론가") or "익명 평론가",
                "리뷰 내용": self._clean_text(r.get("snippet", "")),
                "평점": self._map_score_to_recommend(r.get("score"))
            })
        return result

    # ------------------------------------------------------------------ #
    #  메인 실행                                                           #
    # ------------------------------------------------------------------ #

    def run(self):
        progress = self.load_progress()
        offset = progress["last_offset"]
        processed_ids = progress["processed_ids"]

        print(f"▶ 수집 재개: offset={offset}, 완료된 게임={len(processed_ids)}개")

        # tqdm: 전체 수를 모르므로 동적으로 업데이트
        pbar = tqdm(desc="전체 게임 수집 중", unit="게임")
        pbar.update(len(processed_ids))  # 이미 처리한 수 반영

        while True:
            games_page = self.fetch_game_list_page(offset)

            # None → 요청 자체 실패
            if games_page is None:
                print(f"\n[오류] offset={offset} 페이지 요청 실패. 중단.")
                break

            # 빈 리스트 → 마지막 페이지 도달
            if not games_page:
                print("\n✅ 모든 게임 수집 완료!")
                break

            for game in games_page:
                game_id   = game.get("id")
                game_name = game.get("name", "이름 없음")

                if not game_id or game_id in processed_ids:
                    pbar.update(1)
                    continue

                pbar.set_description(f"수집 중: {game_name}")

                reviews = self.fetch_reviews(game_id, game_name)

                if reviews:
                    with open(self.data_file, "a", encoding="utf-8") as f:
                        for rev in reviews:
                            f.write(json.dumps(rev, ensure_ascii=False) + "\n")
                else:
                    self._log_error(f"리뷰 없음 (id={game_id}): {game_name}")

                processed_ids.add(game_id)
                pbar.update(1)
                time.sleep(0.5)  # API 호출 간격

            # 페이지 단위로 진행 상황 저장
            offset += self.PAGE_SIZE
            self.save_progress(offset, processed_ids)
            time.sleep(1)

        pbar.close()
        print(f"\n📁 저장 위치: {self.data_file}")
        print(f"⚠️  오류 목록: {self.error_log}")


# ------------------------------------------------------------------ #
#  실행                                                               #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    # 보안: API 키를 코드에 직접 넣지 말 것.
    # 환경변수 RAPIDAPI_KEY 로 설정하거나, 아래 기본값을 본인 키로 바꿔 사용.
    #   (Windows cmd)  set RAPIDAPI_KEY=발급받은키
    MY_KEY = os.environ.get("RAPIDAPI_KEY", "여기에_본인_RapidAPI_키_입력")

    if MY_KEY.startswith("여기에"):
        raise SystemExit("RapidAPI 키를 설정하세요. (환경변수 RAPIDAPI_KEY 또는 코드 수정)")

    fetcher = OpenCriticFullFetcher(MY_KEY)
    fetcher.run()
# OpenCritic 크롤러 (초기 시도)

OpenCritic API(RapidAPI)로 게임 평론을 수집하는 크롤러입니다.

> **초기에 사용했다가 전환한 방식입니다.**
> 무료 API의 요청량·데이터 제공량이 한정적이라 표본이 부족해서,
> 최종적으로 **Steam 공개 리뷰**로 전환했습니다. (→ `../steam/`)

## 실행
```cmd
pip install -r requirements.txt
set RAPIDAPI_KEY=발급받은_RapidAPI_키
python OpenCritic_WebCrawler.py
```
- 결과: `reviews_final_data.jsonl`

## 보안
API 키를 코드에 직접 넣지 마세요. **환경변수 `RAPIDAPI_KEY`** 로 설정합니다.

"""에어코리아에서 인천 측정소 실시간 대기질을 받아 data/air.json에 저장합니다.
GitHub Actions가 1시간마다 실행합니다. 인증키는 저장소 Secrets의 AIRKOREA_KEY에서 읽어요.
받기에 실패하면 기존 파일을 그대로 두고 끝냅니다(앱은 마지막 값을 계속 보여줌)."""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

KEY = os.environ.get("AIRKOREA_KEY", "").strip()
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "air.json")
URL = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"

def num(v):
    try:
        return float(v) if "." in str(v) else int(v)
    except (TypeError, ValueError):
        return None

def main():
    if not KEY:
        print("AIRKOREA_KEY가 설정되지 않았어요. 저장소 Settings > Secrets에 등록해 주세요.")
        return 0
    key = KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")
    qs = urllib.parse.urlencode({"returnType": "json", "numOfRows": 100, "pageNo": 1, "sidoName": "인천", "ver": "1.0"})
    try:
        with urllib.request.urlopen(f"{URL}?serviceKey={key}&{qs}", timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("대기질을 받지 못했어요:", e)
        return 0
    head = body.get("response", {}).get("header", {})
    if head.get("resultCode") != "00":
        print("API 오류:", head)
        return 0
    rows = body["response"]["body"]["items"]
    items = {a["stationName"]: {"pm10": num(a.get("pm10Value")), "pm25": num(a.get("pm25Value"))} for a in rows}
    times = [a["dataTime"] for a in rows if a.get("dataTime")]
    out = {
        "time": max(times) if times else "",
        "fetchedAt": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"),
        "items": items,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("저장 완료:", out["time"], len(items), "개 측정소")
    return 0

if __name__ == "__main__":
    sys.exit(main())

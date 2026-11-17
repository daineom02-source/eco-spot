"""기상청 단기예보를 받아 data/weather.json에 저장합니다.
GitHub Actions가 1시간마다 실행합니다. 인증키는 에어코리아와 같은 공공데이터포털 키(AIRKOREA_KEY)를 씁니다.
(공공데이터포털에서 '기상청_단기예보 조회서비스' 활용신청이 되어 있어야 합니다)
받기에 실패하면 기존 파일을 그대로 두고 끝냅니다."""
import json, math, os, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

KEY = os.environ.get("AIRKOREA_KEY", "").strip()
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "weather.json")
URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
KST = timezone(timedelta(hours=9))

# 사업소 위치 (앱의 시설 좌표와 같음)
SITES = {
    "청라사업소": (37.552908, 126.618681),
    "가좌사업소": (37.4926, 126.6634),
    "공촌사업소": (37.5608, 126.6258),
    "송도지소": (37.3694, 126.6631),
    "운북사업소": (37.5136, 126.4969),
    "송산지소": (37.4793, 126.4735),
    "송도사업소": (37.3478, 126.6154),
}

def to_grid(lat, lon):
    """위경도 -> 기상청 격자(nx, ny). 기상청 공식 변환식(LCC)."""
    RE, GRID, SLAT1, SLAT2, OLON, OLAT, XO, YO = 6371.00877, 5.0, 30.0, 60.0, 126.0, 38.0, 43, 136
    D = math.pi / 180.0
    re = RE / GRID
    s1, s2, olon, olat = SLAT1 * D, SLAT2 * D, OLON * D, OLAT * D
    sn = math.log(math.cos(s1) / math.cos(s2)) / math.log(math.tan(math.pi * 0.25 + s2 * 0.5) / math.tan(math.pi * 0.25 + s1 * 0.5))
    sf = math.pow(math.tan(math.pi * 0.25 + s1 * 0.5), sn) * math.cos(s1) / sn
    ro = re * sf / math.pow(math.tan(math.pi * 0.25 + olat * 0.5), sn)
    ra = re * sf / math.pow(math.tan(math.pi * 0.25 + lat * D * 0.5), sn)
    theta = lon * D - olon
    if theta > math.pi: theta -= 2 * math.pi
    if theta < -math.pi: theta += 2 * math.pi
    theta *= sn
    return int(ra * math.sin(theta) + XO + 0.5), int(ro - ra * math.cos(theta) + YO + 0.5)

def base_time(now):
    """가장 최근에 발표된 단기예보 시각 (발표 후 15분 여유)."""
    t = now - timedelta(minutes=15)
    for h in (23, 20, 17, 14, 11, 8, 5, 2):
        if t.hour >= h:
            return t.strftime("%Y%m%d"), f"{h:02d}00"
    y = t - timedelta(days=1)
    return y.strftime("%Y%m%d"), "2300"

def fetch(nx, ny, bd, bt, key):
    qs = urllib.parse.urlencode({"pageNo": 1, "numOfRows": 1000, "dataType": "JSON",
                                 "base_date": bd, "base_time": bt, "nx": nx, "ny": ny})
    with urllib.request.urlopen(f"{URL}?serviceKey={key}&{qs}", timeout=30) as r:
        body = json.loads(r.read().decode("utf-8"))
    head = body.get("response", {}).get("header", {})
    if head.get("resultCode") != "00":
        raise RuntimeError(f"API 오류: {head}")
    return body["response"]["body"]["items"]["item"]

def hours_from(items, now):
    by = {}
    for it in items:
        k = f'{it["fcstDate"]}{it["fcstTime"]}'
        by.setdefault(k, {})[it["category"]] = it["fcstValue"]
    out = []
    start = now.strftime("%Y%m%d%H00")
    for k in sorted(by):
        if k < start: continue
        v = by[k]
        def n(x):
            try: return float(x)
            except (TypeError, ValueError): return None
        out.append({"t": f"{k[:4]}-{k[4:6]}-{k[6:8]} {k[8:10]}:00",
                    "tmp": n(v.get("TMP")), "pop": n(v.get("POP")),
                    "pty": int(v.get("PTY", 0) or 0), "sky": int(v.get("SKY", 1) or 1)})
        if len(out) >= 24: break
    return out

def main():
    if not KEY:
        print("AIRKOREA_KEY가 없어요. 저장소 Settings > Secrets에 등록해 주세요.")
        return 0
    key = KEY if "%" in KEY else urllib.parse.quote(KEY, safe="")
    now = datetime.now(KST)
    bd, bt = base_time(now)
    grids, sites = {}, {}
    for name, (lat, lon) in SITES.items():
        nx, ny = to_grid(lat, lon)
        try:
            if (nx, ny) not in grids:
                grids[(nx, ny)] = hours_from(fetch(nx, ny, bd, bt, key), now)
        except Exception as e:
            print(name, "예보를 받지 못했어요:", e)
            continue
        sites[name] = {"nx": nx, "ny": ny, "hours": grids[(nx, ny)]}
    if not sites:
        print("받은 예보가 없어 기존 파일을 유지합니다.")
        return 0
    out = {"base": f"{bd[:4]}-{bd[4:6]}-{bd[6:]} {bt[:2]}:{bt[2:]}",
           "fetchedAt": now.strftime("%Y-%m-%d %H:%M"), "sites": sites}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("저장 완료:", out["base"], "발표,", len(sites), "개 사업소")
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# 원본(네이버 주문 메뉴, biz 1346907) + 표준 영양데이터 → 메뉴별 영양성분 계산 → data/menus.json
# 재검증용: 값 수정은 ingredients.json / 이 파일의 composition 규칙만 고치면 됨.
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = json.load(open(os.path.join(ROOT, "build", "naver_order_raw.json"), encoding="utf-8"))
ing = json.load(open(os.path.join(ROOT, "data", "ingredients.json"), encoding="utf-8"))
P100 = ing["per100g"]; PS = ing["perServing"]; VEG = ing["vegRule"]

# 네이버 주문 카테고리명 → 내부 카테고리 코드
def primary_category(m):
    names = [n for n in m["categoryNames"] if n != "추천"]
    n = names[0] if names else (m["categoryNames"][0] if m["categoryNames"] else "")
    return {
        "그릴드 덮밥": "덮밥",
        "그릴드 파스타": "파스타",
        "일본식 카레라이스": "카레",
        "그릴드 샐러드": "샐러드",
        "음료": "음료",
        "사이드": "사이드",
        "그릴드 특제 소스": "소스",
        "그릴박스 세트메뉴": "세트",
        "요일별 특가": "특가",
    }.get(n, "기타")

def meat_key(name):
    # 치킨렉(닭다리)를 반드시 '치킨'보다 먼저 판정
    if "치킨렉" in name or "닭다리" in name: return "chicken_leg"
    if "삼겹" in name: return "pork_belly"
    if "비프" in name: return "beef_chuck"
    if "치킨" in name: return "chicken_breast"
    return None

def meat_grams(name):
    if "3XL" in name: return 500
    if "2XL" in name: return 300
    return 200

def from100(key, grams):
    v = P100[key]; f = grams / 100.0
    return v["kcal"]*f, v["protein"]*f, v["carb"]*f, v["fat"]*f

def add(acc, t):
    acc["kcal"] += t[0]; acc["protein"] += t[1]; acc["carb"] += t[2]; acc["fat"] += t[3]

def add_veg(cat, acc, basis):
    # 형 확정 스펙: 덮밥·파스타 = 로메인35+적근대35, 샐러드 = 로메인70+적근대70
    rule = VEG.get(cat)
    if not rule:
        return
    for k, g in rule.items():
        add(acc, from100(k, g))
    basis.append("로메인 %dg" % rule["romaine"])
    basis.append("적근대 %dg" % rule["red_chard"])

def compute(cat, name):
    """핵심 식사 4종만 영양 산출. 그 외는 (None, [], status)."""
    mk = meat_key(name)
    acc = {"kcal": 0.0, "protein": 0.0, "carb": 0.0, "fat": 0.0}
    basis = []
    if cat in ("덮밥", "파스타", "카레", "샐러드"):
        if mk is None:
            return None, [], "pending"
        g = meat_grams(name)
        if cat == "카레":
            add(acc, from100("rice_white", 180)); basis.append("흰쌀밥 180g")
            cs = PS["curry_sauce"]; add(acc, (cs["kcal"], cs["protein"], cs["carb"], cs["fat"])); basis.append("일본식 카레소스 1인분")
        elif cat == "덮밥":
            add(acc, from100("rice_white", 180)); basis.append("흰쌀밥 180g")
        elif cat == "파스타":
            add(acc, from100("pasta_durum", 150)); basis.append("듀럼밀 파스타 150g")
        # 고기
        add(acc, from100(mk, g))
        basis.append(f"{P100[mk]['라벨'].split('(')[1].split(')')[0]} {g}g")
        # 채소(덮밥·파스타·샐러드만; 카레 제외). 샐러드 = 고기+채소가 전부.
        add_veg(cat, acc, basis)
        return acc, basis, "estimated"
    return None, [], "excluded" if cat in ("음료", "특가") else "pending"

CAT_ORDER = {"덮밥": 0, "파스타": 1, "카레": 2, "샐러드": 3, "세트": 4, "사이드": 5, "소스": 6, "특가": 7, "음료": 8, "기타": 9}

def base_image_map(items):
    m = {}
    for it in items:
        if it["image"] and it["category"] in ("덮밥","파스타","카레","샐러드"):
            key = (it["category"], meat_key(it["name"]))
            m.setdefault(key, it["image"])
    return m

items = []
for r in raw:
    cat = primary_category(r)
    nut, basis, status = compute(cat, r["name"])
    items.append({
        "id": r["id"], "name": r["name"], "category": cat, "price": r["price"],
        "description": r["desc"], "image": r["image"], "order": r.get("order", 0),
        "nutrition": None if nut is None else {
            "kcal": round(nut["kcal"]), "protein": round(nut["protein"], 1),
            "carb": round(nut["carb"], 1), "fat": round(nut["fat"], 1)},
        "sodium": "미제공",
        "basis": basis, "status": status,
    })

imgmap = base_image_map(items)
for it in items:
    if not it["image"] and it["category"] in ("덮밥","파스타","카레","샐러드"):
        it["image"] = imgmap.get((it["category"], meat_key(it["name"])))

# 페이지 표시 대상 = 핵심 식사 4종(덮밥/파스타/카레/샐러드). 음료·특가·중복 제외.
core = [it for it in items if it["category"] in ("덮밥","파스타","카레","샐러드")]
core.sort(key=lambda e: (CAT_ORDER[e["category"]], e["id"]))

allitems = sorted(items, key=lambda e: (CAT_ORDER.get(e["category"],9), e.get("order",0), e["id"]))

result = {
    "_meta": {
        "source": "네이버 주문 — 그릴박스 노량진점 (place 1093880694 / order biz 1346907)",
        "collected": "2026-07-10 재수집(전 카테고리)",
        "disclaimer": "표기값은 재료·표준 영양데이터 기반 추정치이며 실제와 차이가 있을 수 있습니다. 정밀 실측 아님.",
        "표기항목": ["칼로리(kcal)", "단백질(g)", "탄수화물(g)", "지방(g)", "나트륨(미제공)"],
        "core_count": len(core),
        "total_menu_count": len(items),
    },
    "menus": core,
    "_all": allitems,
}
json.dump(result, open(os.path.join(ROOT, "data", "menus.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

from collections import Counter
tally = Counter(it["category"] for it in items)
print(f"wrote data/menus.json — core(표시) {len(core)} / total {len(items)}")
print("category tally:", dict(tally))

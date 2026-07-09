#!/usr/bin/env python3
# 원본(네이버 플레이스) 메뉴 + 표준 영양데이터 → 메뉴별 영양성분 계산 → data/menus.json 생성
# 재검증용: 값 수정은 ingredients.json / 이 파일의 composition 규칙만 고치면 됨.
import json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = json.load(open(os.path.join(ROOT, "build", "naver_menus_raw.json"), encoding="utf-8"))
ing = json.load(open(os.path.join(ROOT, "data", "ingredients.json"), encoding="utf-8"))
P100 = ing["per100g"]; PS = ing["perServing"]

def meat_key(name):
    if "비프" in name and "포크" in name: return "combo"
    if "치킨" in name: return "chicken_steak"
    if "포크" in name: return "pork_steak"
    if "비프" in name: return "beef_chuck"
    return None

def meat_grams(name):
    if "3XL" in name: return 500
    if "2XL" in name: return 300
    return 200

def add(acc, kcal, protein, carb, fat):
    acc["kcal"] += kcal; acc["protein"] += protein; acc["carb"] += carb; acc["fat"] += fat

def from100(key, grams):
    v = P100[key]; f = grams / 100.0
    return v["kcal"]*f, v["protein"]*f, v["carb"]*f, v["fat"]*f

def compute(name):
    """returns (category, nutrition|None, basis_list)"""
    acc = {"kcal": 0.0, "protein": 0.0, "carb": 0.0, "fat": 0.0}
    basis = []
    mk = meat_key(name)

    if "카레라이스" in name:
        cat = "덮밥"
        add(acc, *from100("rice_white", 180)); basis.append("흰쌀밥 180g")
        cs = PS["curry_sauce"]; add(acc, cs["kcal"], cs["protein"], cs["carb"], cs["fat"]); basis.append("일본식 카레소스 1인분")
        add(acc, *from100(mk, 200)); basis.append(f"{P100[mk]['라벨'].split()[1]} 200g")
        return cat, acc, basis

    if "덮밥" in name or "파스타" in name:
        is_pasta = "파스타" in name
        cat = "파스타" if is_pasta else "덮밥"
        base_key = "pasta_durum" if is_pasta else "rice_white"
        base_g = 150 if is_pasta else 180
        add(acc, *from100(base_key, base_g)); basis.append(f"{P100[base_key]['라벨'].split()[0]} {base_g}g")
        if mk == "combo":
            add(acc, *from100("beef_chuck", 100)); add(acc, *from100("pork_steak", 100))
            basis.append("직화 비프 100g + 직화 포크 100g")
        else:
            g = meat_grams(name); add(acc, *from100(mk, g))
            basis.append(f"{P100[mk]['라벨'].split()[1]} {g}g")
        return cat, acc, basis

    # 음료
    if "아메리카노" in name:
        v = PS["americano"]; return "음료", {"kcal": v["kcal"], "protein": v["protein"], "carb": v["carb"], "fat": v["fat"]}, ["아메리카노 벤티"]
    if "제로" in name or "콜라" in name or "스프라이트" in name or "에너지드링크" in name:
        v = PS["zero_drink"]; return "음료", {"kcal": v["kcal"], "protein": v["protein"], "carb": v["carb"], "fat": v["fat"]}, ["제로 음료(제로칼로리 표기)"]

    return "기타", None, []  # 계산 불가 → 정보 확인 중

CAT_ORDER = {"덮밥": 0, "파스타": 1, "음료": 2, "기타": 3}
out = []
for m in raw:
    name = m["name"]
    cat, nut, basis = compute(name)
    if cat == "음료":  # 음료 메뉴는 페이지에서 제외(재생성 시에도 유입 차단)
        continue
    imgs = m.get("images") or []
    entry = {
        "id": m.get("id"),
        "name": name,
        "category": cat,
        "price": m.get("price"),
        "description": (m.get("description") or "").replace("\n", " ").strip(),
        "image": imgs[0] if imgs else None,
        "nutrition": None if nut is None else {
            "kcal": round(nut["kcal"]),
            "protein": round(nut["protein"], 1),
            "carb": round(nut["carb"], 1),
            "fat": round(nut["fat"], 1)
        },
        "basis": basis,
        "status": "estimated" if nut is not None else "pending"
    }
    out.append(entry)

out.sort(key=lambda e: (CAT_ORDER.get(e["category"], 9), e["id"]))
result = {
    "_meta": {
        "source": "네이버 플레이스 — 그릴박스 노량진점 (placeId 1093880694)",
        "disclaimer": "표기값은 재료·표준 영양데이터 기반 추정치이며 실제와 차이가 있을 수 있습니다. 정밀 실측 아님.",
        "표기항목": ["칼로리(kcal)", "단백질(g)", "탄수화물(g)", "지방(g)"],
        "count": len(out)
    },
    "menus": out
}
json.dump(result, open(os.path.join(ROOT, "data", "menus.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"wrote data/menus.json ({len(out)} menus)")
for e in out:
    n = e["nutrition"]
    s = f'{n["kcal"]}kcal P{n["protein"]} C{n["carb"]} F{n["fat"]}' if n else "정보 확인 중"
    print(f'  [{e["category"]}] {e["name"]:<22} {s}')

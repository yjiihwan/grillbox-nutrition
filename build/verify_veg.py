#!/usr/bin/env python3
# 형 확정 스펙(2026-07-10 채소·고기매핑) 검증 게이트.
# 각 메뉴 총영양소 = 고기 + (밥/면/카레) + 채소 를 독립 재계산해 menus.json과 대조.
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ing = json.load(open(os.path.join(ROOT, "data", "ingredients.json"), encoding="utf-8"))
menus = json.load(open(os.path.join(ROOT, "data", "menus.json"), encoding="utf-8"))
P = ing["per100g"]; PS = ing["perServing"]; VEG = ing["vegRule"]

def per(k, g):
    v = P[k]; f = g/100.0
    return [v["kcal"]*f, v["protein"]*f, v["carb"]*f, v["fat"]*f]
def add(a, b): return [a[i]+b[i] for i in range(4)]

def meat_key(n):
    if "치킨렉" in n: return "chicken_leg"
    if "삼겹" in n: return "pork_belly"
    if "비프" in n: return "beef_chuck"
    if "치킨" in n: return "chicken_breast"
    return None
def grams(n): return 500 if "3XL" in n else 300 if "2XL" in n else 200

def expected(cat, name):
    acc = [0,0,0,0]; mk = meat_key(name); g = grams(name)
    if cat == "카레":
        acc = add(acc, per("rice_white",180))
        cs = PS["curry_sauce"]; acc = add(acc, [cs["kcal"],cs["protein"],cs["carb"],cs["fat"]])
    elif cat == "덮밥": acc = add(acc, per("rice_white",180))
    elif cat == "파스타": acc = add(acc, per("pasta_durum",150))
    acc = add(acc, per(mk, g))
    rule = VEG.get(cat)
    if rule:
        acc = add(acc, per("romaine", rule["romaine"]))
        acc = add(acc, per("red_chard", rule["red_chard"]))
    return [round(acc[0]), round(acc[1],1), round(acc[2],1), round(acc[3],1)]

EXCLUDE = {"세트","소스","음료","특가","사이드"}
fails = []; checked = 0

# 게이트1: 제외 항목이 표시목록(menus)에 없어야
disp_cats = {m["category"] for m in menus["menus"]}
g1 = EXCLUDE & disp_cats
print(f"[G1 제외] 표시목록 카테고리={sorted(disp_cats)} / 제외교집합={sorted(g1)} -> {'PASS' if not g1 else 'FAIL'}")

# 게이트2: 산술 재계산 대조 (전 표시메뉴)
VEGSET = {"덮밥","파스타","샐러드"}
g3_veg_ok = True
for m in menus["menus"]:
    cat, name, n = m["category"], m["name"], m["nutrition"]
    exp = expected(cat, name)
    got = [n["kcal"], n["protein"], n["carb"], n["fat"]]
    checked += 1
    if any(abs(exp[i]-got[i])>0.15 for i in range(4)):
        fails.append((name, exp, got))
    # 게이트3: 채소 반영/미반영 확인 (basis 문자열)
    has_veg = ("로메인" in " ".join(m["basis"])) and ("적근대" in " ".join(m["basis"]))
    if cat in VEGSET and not has_veg: g3_veg_ok = False; print("  VEG누락:", name)
    if cat == "카레" and has_veg: g3_veg_ok = False; print("  카레에 채소 오반영:", name)

print(f"[G2 산술] 대조 {checked}종 -> {'PASS' if not fails else 'FAIL('+str(len(fails))+')'}")
for f in fails[:10]: print("   MISMATCH", f)
print(f"[G3 채소] 덮밥/파스타/샐러드 채소반영 & 카레 미반영 -> {'PASS' if g3_veg_ok else 'FAIL'}")

# 게이트4: 고기매핑 스팟(칼로리 순서: 치킨<치킨렉<비프<삼겹, 동일카테고리 기본사이즈)
def kcal(cat, meat):
    for m in menus["menus"]:
        if m["category"]==cat and meat in m["name"] and "2XL" not in m["name"] and "3XL" not in m["name"]:
            if meat=="치킨" and "치킨렉" in m["name"]: continue
            return m["nutrition"]["kcal"]
    return None
order_ok = True
for cat in ["덮밥","샐러드"]:
    ck,cl,bf,sp = kcal(cat,"치킨"),kcal(cat,"치킨렉"),kcal(cat,"비프"),kcal(cat,"삼겹")
    ok = ck < cl < bf < sp
    order_ok = order_ok and ok
    print(f"[G4 고기] {cat}: 치킨{ck} < 치킨렉{cl} < 비프{bf} < 삼겹{sp} -> {'PASS' if ok else 'FAIL'}")

allpass = (not g1) and (not fails) and g3_veg_ok and order_ok
print("\n=== " + ("ALL PASS ✅" if allpass else "FAIL ❌") + " ===")
sys.exit(0 if allpass else 1)

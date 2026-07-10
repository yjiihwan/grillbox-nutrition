// 메뉴 데이터(JSON)를 읽어 카드 렌더 + 카테고리 필터.
// 정렬은 데이터에 하드코딩하지 않는다. 각 메뉴 이름에서 (카테고리·고기·사이즈) 축을
// 추출해 계층형으로 정렬하므로, 메뉴가 추가돼도 아래 순서표(ORDER 상수)만 지키면 자동 정렬된다.
// 새 카테고리/고기/사이즈를 지원하려면 해당 순서표에 항목만 추가하면 된다.

// ── 분류 순서표(설정) ─────────────────────────────────────────────
// 1) 카테고리: 덮밥 → 파스타 → 카레. 정의 안 된 카테고리는 맨뒤(rank 99).
//    detection precedence는 배열 순서(구체적인 것 먼저)라 "카레라이스"가 덮밥으로 새지 않는다.
const CATEGORIES = [
  { key: "카레", rank: 2, match: (n) => n.includes("카레") },
  { key: "파스타", rank: 1, match: (n) => n.includes("파스타") },
  { key: "덮밥", rank: 0, match: (n) => n.includes("덮밥") },
];
// 필터 칩 표시 순서(정렬 우선순위와 동일)
const CAT_CHIPS = ["전체", "덮밥", "파스타", "카레"];

// 2) 고기: 닭 → 돼지 → 소. 단일 고기 뒤에 복합(2종+), 그 뒤에 미정의.
const MEATS = [
  { key: "닭", rank: 0, match: (n) => n.includes("치킨") },
  { key: "돼지", rank: 1, match: (n) => n.includes("포크") },
  { key: "소", rank: 2, match: (n) => n.includes("비프") },
];

// 3) 사이즈: 무표기(기본) → XL → 2XL → 3XL. 긴 토큰 먼저 검사(2XL이 XL로 새지 않도록).
const SIZE_TOKENS = ["3XL", "2XL", "XL"];

// ── 분류 함수 ─────────────────────────────────────────────────────
function categoryOf(name) {
  return CATEGORIES.find((c) => c.match(name)) || null;
}
function meatRank(name) {
  const hit = MEATS.filter((m) => m.match(name));
  if (hit.length === 0) return MEATS.length + 1; // 미정의 → 맨뒤
  if (hit.length === 1) return hit[0].rank;
  return MEATS.length; // 복합(2종+) → 단일 고기 뒤, 미정의 앞
}
function sizeRank(name) {
  const t = SIZE_TOKENS.find((s) => name.includes(s));
  if (!t) return 0; // 무표기 = 기본
  const num = parseInt(t, 10); // "3XL"→3, "2XL"→2, "XL"→NaN
  return Number.isNaN(num) ? 1 : num; // XL은 무표기와 2XL 사이
}
function classify(m) {
  const cat = categoryOf(m.name);
  return {
    ...m,
    category: cat ? cat.key : m.category || "기타", // 파생 카테고리로 덮어씀(배지·필터 일관)
    _catRank: cat ? cat.rank : 99,
    _meatRank: meatRank(m.name),
    _sizeRank: sizeRank(m.name),
  };
}
function sortMenus(list) {
  return [...list].sort(
    (a, b) =>
      a._catRank - b._catRank || a._meatRank - b._meatRank || a._sizeRank - b._sizeRank
  );
}

let ALL = [];
let active = "전체";

// 계산근거 블록 화면 노출 토글. 데이터(m.basis)·로직은 유지, 렌더만 skip. 되살리려면 true.
const SHOW_BASIS = false;

function nutriBlock(m) {
  if (m.status === "pending" || !m.nutrition) {
    return `<div class="nutri pending"><div class="cell">영양 정보 확인 중</div></div>`;
  }
  const n = m.nutrition;
  const basis = SHOW_BASIS
    ? `<div class="basis">계산 근거: ${m.basis.join(" + ")}</div>`
    : "";
  return `
    <div class="nutri">
      <div class="cell kcal"><div class="lab">칼로리</div><div class="val">${n.kcal}<span class="u">kcal</span></div></div>
      <div class="cell protein"><div class="lab">단백질</div><div class="val">${n.protein}<span class="u">g</span></div></div>
      <div class="cell carb"><div class="lab">탄수화물</div><div class="val">${n.carb}<span class="u">g</span></div></div>
      <div class="cell fat"><div class="lab">지방</div><div class="val">${n.fat}<span class="u">g</span></div></div>
    </div>
    ${basis}
    <span class="est-tag">추정치</span>`;
}

function cardHTML(m) {
  const img = m.image
    ? `<img src="${m.image}" alt="${m.name}" loading="lazy"
         onerror="this.parentElement.innerHTML='<div class=&quot;noimg&quot;>이미지 준비 중</div>'">`
    : `<div class="noimg">이미지 준비 중</div>`;
  return `
    <article class="card" data-cat="${m.category}">
      <div class="thumb"><span class="cat-badge">${m.category}</span>${img}</div>
      <div class="body">
        <div class="name">${m.name}</div>
        <div class="desc">${m.description || ""}</div>
        ${nutriBlock(m)}
      </div>
    </article>`;
}

function render() {
  const grid = document.getElementById("grid");
  const list = active === "전체" ? ALL : ALL.filter((m) => m.category === active);
  grid.innerHTML = list.map(cardHTML).join("");
}

function buildTabs() {
  const wrap = document.getElementById("tabs");
  wrap.innerHTML = CAT_CHIPS.map(
    (c) => `<button class="tab${c === active ? " active" : ""}" data-cat="${c}">${c}</button>`
  ).join("");
  wrap.querySelectorAll(".tab").forEach((b) =>
    b.addEventListener("click", () => {
      active = b.dataset.cat;
      wrap.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === b));
      render();
    })
  );
}

async function init() {
  const res = await fetch("data/menus.json");
  const data = await res.json();
  // 분류(카테고리·고기·사이즈) 부여 후 계층 정렬. 원본 JSON 순서에 의존하지 않는다.
  ALL = sortMenus(data.menus.map(classify));
  // 계산근거성 서술(재료·데이터 기반 방법론) 비노출 → index.html의 짧은 disclaimer 유지.
  // 되살리려면 아래 주석 해제. 데이터(_meta.disclaimer)는 그대로 남김.
  // document.getElementById("disc").textContent = "※ " + data._meta.disclaimer;
  buildTabs();
  render();
}
init();

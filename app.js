// 메뉴 데이터(JSON)를 읽어 카드 렌더 + 카테고리 필터. 데이터는 코드에 하드코딩하지 않음.
const CATS = ["전체", "덮밥", "파스타", "음료"];
let ALL = [];
let active = "전체";

const won = (n) => (n == null ? "-" : n.toLocaleString("ko-KR") + "원");

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
        <div class="price">${won(m.price)}</div>
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
  wrap.innerHTML = CATS.map(
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
  ALL = data.menus;
  // 계산근거성 서술(재료·데이터 기반 방법론) 비노출 → index.html의 짧은 disclaimer 유지.
  // 되살리려면 아래 주석 해제. 데이터(_meta.disclaimer)는 그대로 남김.
  // document.getElementById("disc").textContent = "※ " + data._meta.disclaimer;
  buildTabs();
  render();
}
init();

(function () {
  "use strict";

  var LEVEL_DOTS = { "입문": 1, "중급": 2, "심화": 3 };
  var SLOT_LABEL = { "new": "신간 추천", "steady": "스테디 추천" };
  var SECTION_COLORS = {
    total: "#5856d6", theology: "#af52de", commentary: "#0a7aff", faith: "#ff5e3a",
    bible: "#d97a00", intro: "#28a745", history: "#a2845e"
  };
  var COLORS = { ot: "#b5651d", nt: "#5856d6", commentary: "#0a7aff", doctrine: "#af52de", history: "#1d9e75", picks: "#d97a00" };
  var VIEWS = [
    { key: "now", label: "이번 주" },
    { key: "steady", label: "스테디" },
    { key: "rising", label: "급상승" },
    { key: "new", label: "신규 진입" }
  ];
  var PRODUCT = document.body.getAttribute("data-product") || "charts";
  var state = { data: null, groups: [], active: null };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- 책 카드 조각들 ---------- */
  function deltaHTML(b) {
    if (b.isNew) return '<span class="d new">NEW</span>';
    if (b.delta === null || b.delta === undefined) return "";
    if (b.delta > 0) return '<span class="d up">▲ ' + b.delta + "</span>";
    if (b.delta < 0) return '<span class="d down">▼ ' + Math.abs(b.delta) + "</span>";
    return '<span class="d same">—</span>';
  }

  function bookImg(b, cls) {
    if (b.cover) {
      var large = (cls === "xl" || cls === "pod") && b.coverLarge && b.coverLarge !== b.cover;
      var src = large ? b.coverLarge : b.cover;
      var fallback = large ? ' onerror="this.onerror=null;this.src=\'' + esc(b.cover) + '\'"' : "";
      return '<div class="bk ' + cls + '"><img src="' + esc(src) + '" alt="" loading="lazy"' + fallback + "></div>";
    }
    var ch = (b.title || "책").trim().charAt(0);
    return '<div class="bk ' + cls + ' ph" aria-hidden="true">' + esc(ch) + "</div>";
  }

  function dotsHTML(level) {
    var n = LEVEL_DOTS[level] || 0;
    var out = '<span class="dots" aria-hidden="true">';
    for (var i = 1; i <= 3; i++) out += '<span class="dot' + (i <= n ? " on" : "") + '"></span>';
    return out + "</span>";
  }

  function stripHTML(c) {
    var parts = [];
    if (c.rating != null) parts.push('<span><span class="star">★</span> ' + c.rating.toFixed(1) + "</span>");
    if (c.level) parts.push("<span>" + dotsHTML(c.level) + esc(c.level) + "</span>");
    if (c.tradition) parts.push("<span>" + esc(c.tradition) + "</span>");
    return parts.join('<span class="sep">·</span>');
  }

  function byline(b) {
    return [b.author, b.publisher].filter(Boolean).join(" · ");
  }

  function streakHTML(b, tag) {
    return b.streak > 1 ? "<" + tag + ' class="streak">' + b.streak + "주 연속</" + tag + ">" : "";
  }

  function recChips(b) {
    if (!b.recommenders || !b.recommenders.length) return "";
    return '<div class="recs">' + b.recommenders.map(function (r) {
      return '<span class="rec">추천 · ' + esc(r.name) + "</span>";
    }).join("") + "</div>";
  }

  function recBlock(b) {
    if (!b.recommenders || !b.recommenders.length) return "";
    return '<div class="rec-block">' + b.recommenders.map(function (r) {
      return '<div class="rec-item"><span class="rec-who">' + esc(r.name) + (r.school ? " · " + esc(r.school) : "") +
        (r.top ? ' <span class="rec-top">딱 한 권</span>' : "") + "</span>" +
        (r.reason ? '<p class="rec-reason">“' + esc(r.reason) + "”</p>" : "") + "</div>";
    }).join("") + "</div>";
  }

  function featuredCard(f) {
    var own = f.own ? '<span class="ft-own">우리 책</span>' : "";
    var style = f.accent ? ' style="--accent:' + esc(f.accent) + '"' : "";
    return (
      '<a class="ft ft-quiet" href="' + esc(f.link) + '" target="_blank" rel="noopener"' + style + ">" +
      bookImg(f, "ft-md") +
      '<div class="ft-body"><div class="ft-label">' + esc(SLOT_LABEL[f.slot] || f.label || "이번 주 추천") + own + "</div>" +
      '<div class="ft-title">' + esc(f.title) + "</div>" +
      '<div class="ft-by">' + esc(f.author) + "</div>" +
      (f.blurb ? '<p class="ft-blurb">' + esc(f.blurb) + "</p>" : "") +
      '<span class="ft-cta">자세히 보기 ›</span></div></a>'
    );
  }

  function featuredHTML() {
    var list = (state.data.featured || []).filter(function (f) { return f.slot === "new"; });
    if (!list.length) return "";
    var wk = parseInt((state.data.week || "").replace(/\D/g, ""), 10) || 0;
    return '<div class="featured">' + featuredCard(list[wk % list.length]) + "</div>";
  }

  function detailHTML(b) {
    var meta = [b.publisher, b.pubDate ? b.pubDate.slice(0, 7).replace("-", ".") + " 출간" : "", b.category]
      .filter(Boolean).join(" · ");
    var sub = b.subtitle ? '<div class="detail-sub">' + esc(b.subtitle) + "</div>" : "";
    var desc = b.description
      ? '<p class="desc">' + esc(b.description).replace(/\n/g, "<br>") + "</p>"
      : '<p class="desc muted">소개글이 없는 책입니다.</p>';
    return recBlock(b) + sub + desc + (meta ? '<div class="detail-meta">' + esc(meta) + "</div>" : "") +
      '<a class="buy" href="' + esc(b.link) + '" target="_blank" rel="noopener">알라딘에서 보기 ›</a>';
  }

  function podiumHTML(b) {
    var c = b.curation;
    return (
      '<div class="pod" data-id="' + esc(b.id) + '">' +
      '<div class="pod-head"><span class="pod-rank r' + b.rank + '">' + b.rank + "</span>" +
      '<div class="meta">' + deltaHTML(b) + streakHTML(b, "div") + "</div></div>" +
      bookImg(b, "pod") +
      '<a class="pod-title" href="' + esc(b.link) + '" target="_blank" rel="noopener">' + esc(b.title) + "</a>" +
      '<div class="pod-by">' + esc(byline(b)) + "</div>" + recChips(b) +
      (c ? '<div class="pod-strip">' + stripHTML(c) + "</div>" : "") +
      (c && c.quote ? '<p class="pod-quote">“' + esc(c.quote) + "”</p>" : "") +
      '<a class="buy" href="' + esc(b.link) + '" target="_blank" rel="noopener">알라딘에서 보기 ›</a>' +
      "</div>"
    );
  }

  function curationHTML(c) {
    var html = '<div class="cur"><div class="cur-strip">' + stripHTML(c) + "</div>";
    if (c.quote) html += '<p class="quote">“' + esc(c.quote) + "”</p>";
    if (c.badges && c.badges.length) {
      html += '<div class="badges">' + c.badges.map(function (t) {
        return '<span class="badge">' + esc(t) + "</span>";
      }).join("") + "</div>";
    }
    return html + "</div>";
  }

  function rowHTML(b) {
    var c = b.curation;
    var mark = c && c.rating != null ? '<div class="row-star"><span class="star">★</span> ' + c.rating.toFixed(1) + "</div>" : "";
    return (
      '<li class="row' + (c ? " curated" : "") + '" data-id="' + esc(b.id) + '"><div class="row-top">' +
      '<div class="rank">' + b.rank + "</div>" +
      bookImg(b, "sm") +
      '<div class="info"><a class="title" href="' + esc(b.link) + '" target="_blank" rel="noopener">' + esc(b.title) + "</a>" +
      '<div class="byline">' + esc(byline(b)) + "</div>" + mark + recChips(b) + "</div>" +
      '<div class="meta">' + deltaHTML(b) + streakHTML(b, "div") +
      (b.recommendCount && !b.streak ? '<div class="rec-count">추천 ' + b.recommendCount + "명</div>" : "") +
      '<span class="chev" aria-hidden="true">▾</span></div>' +
      "</div>" +
      '<div class="row-detail">' + (c ? curationHTML(c) + '<div class="detail-rest">' + detailHTML(b) + "</div>" : detailHTML(b)) + "</div>" +
      "</li>"
    );
  }

  /* ---------- 메뉴 구조: 그룹 → 묶음 → 항목 ---------- */
  function renumber(books) {
    return books.map(function (b, i) { var c = Object.assign({}, b); c.rank = i + 1; return c; });
  }

  function applyView(books, view) {
    if (view === "steady") {
      return renumber(books.filter(function (b) { return b.streak > 1; })
        .sort(function (a, b) { return b.streak - a.streak || a.rank - b.rank; }));
    }
    if (view === "rising") {
      return renumber(books.filter(function (b) { return b.delta > 0; })
        .sort(function (a, b) { return b.delta - a.delta || a.rank - b.rank; }));
    }
    if (view === "new") {
      return renumber(books.filter(function (b) { return b.isNew; }));
    }
    return books;
  }

  function topicParts(group) {
    var parts = [];
    (group.topics || []).forEach(function (t) {
      var last = parts[parts.length - 1];
      if (!last || last.name !== (t.part || "")) { last = { name: t.part || "", items: [] }; parts.push(last); }
      last.items.push(t);
    });
    return parts;
  }

  function buildChartGroups(data, topics) {
    var groups = [];
    groups.push({
      key: "weekly", label: "주간 베스트", titleFromPart: true,
      parts: data.sections.map(function (s) {
        return {
          name: s.label, color: SECTION_COLORS[s.key],
          items: VIEWS.map(function (v) { return { key: "w-" + s.key + "-" + v.key, label: v.label, books: applyView(s.books, v.key) }; })
        };
      })
    });
    var tg = (topics && topics.groups) || [];
    var find = function (k) { return tg.find(function (g) { return g.key === k; }); };
    var ot = find("ot"), nt = find("nt");
    var bibleParts = [];
    [ot, nt].forEach(function (g) {
      if (!g) return;
      topicParts(g).forEach(function (p) {
        bibleParts.push({ name: p.name, color: COLORS[g.key], items: p.items });
      });
    });
    if (bibleParts.length) {
      groups.push({
        key: "bible", label: "성경",
        parts: bibleParts.map(function (p) {
          return { name: p.name, color: p.color, items: p.items.map(function (t) { return { key: t.key, label: t.label, books: t.books || [] }; }) };
        })
      });
      groups.push({
        key: "commentary", label: "주석", color: COLORS.commentary,
        parts: bibleParts.map(function (p) {
          return {
            name: p.name,
            items: p.items.map(function (t) {
              return { key: "c-" + t.key, label: t.label, books: renumber((t.books || []).filter(function (b) { return b.kind === "commentary"; })
                .map(function (b) { var c = Object.assign({}, b); c.delta = null; c.isNew = false; return c; })) };
            })
          };
        })
      });
    }
    var theologyParts = ["doctrine", "history"].map(find).filter(Boolean).map(function (g) {
      return { name: g.label, color: COLORS[g.key], items: g.topics.map(function (t) { return { key: t.key, label: t.label, books: t.books || [] }; }) };
    });
    if (theologyParts.length) groups.push({ key: "theology", label: "신학", parts: theologyParts });
    return groups;
  }

  function buildPickGroups(data) {
    var picks = data.picks || { fields: [], recommenders: [] };
    var all = {};
    picks.fields.forEach(function (f) { f.books.forEach(function (b) { all[b.id] = b; }); });
    var byPerson = picks.recommenders.map(function (p, i) {
      var books = Object.keys(all).map(function (id) { return all[id]; })
        .filter(function (b) { return (b.recommenders || []).some(function (r) { return r.name === p.name; }); })
        .sort(function (a, b) { return (b.recScore || 0) - (a.recScore || 0) || a.title.localeCompare(b.title); });
      return { key: "r-" + i, label: p.name, books: renumber(books) };
    });
    return [{
      key: "picks", label: "신학자 추천", color: COLORS.picks,
      parts: [
        { name: "분야별", items: picks.fields.map(function (f, i) { return { key: "f-" + i, label: f.name, books: f.books }; }) },
        { name: "추천자별", items: byPerson }
      ]
    }];
  }

  function locate(key) {
    for (var gi = 0; gi < state.groups.length; gi++) {
      var g = state.groups[gi];
      for (var pi = 0; pi < g.parts.length; pi++) {
        var it = g.parts[pi].items.find(function (t) { return t.key === key; });
        if (it) return { group: g, part: g.parts[pi], item: it };
      }
    }
    return null;
  }

  function firstUsable(items) {
    return items.find(function (t) { return t.books && t.books.length; }) || items[0];
  }

  function select(key) {
    state.active = key;
    if (history.replaceState) history.replaceState(null, "", "#" + key);
    renderNav();
    renderList();
  }

  function renderNav() {
    var nav = document.getElementById("tabs");
    var where = locate(state.active);
    if (!where) return;
    var g = where.group, p = where.part, it = where.item;

    var groupsHTML = state.groups.length > 1
      ? '<div class="cas-row cas-groups">' + state.groups.map(function (x) {
        return '<button type="button" class="cas-group' + (x === g ? " on" : "") + '" data-group="' + esc(x.key) + '">' + esc(x.label) + "</button>";
      }).join("") + "</div>"
      : "";
    var partsHTML = '<div class="cas-row cas-parts">' + g.parts.map(function (x) {
      return '<button type="button" class="cas-part' + (x === p ? " on" : "") + '" data-part="' + esc(x.name) + '">' + esc(x.name) + "</button>";
    }).join("") + "</div>";
    var itemsHTML = '<div class="cas-row cas-books">' + p.items.map(function (t) {
      var has = t.books && t.books.length;
      return '<button type="button" class="chip-book' + (t === it ? " on" : "") + (has ? "" : " off") +
        '" data-key="' + esc(t.key) + '"' + (has ? "" : ' disabled title="해당하는 책이 없습니다"') + ">" + esc(t.label) + "</button>";
    }).join("") + "</div>";

    var title = g.titleFromPart ? p.name : it.label;
    var crumb = g.titleFromPart ? g.label + (it.label !== VIEWS[0].label ? " · " + it.label : "") : g.label + " · " + p.name;

    nav.innerHTML = groupsHTML + partsHTML + itemsHTML +
      '<div class="cas-current"><div><span class="cas-crumb">' + esc(crumb) + "</span>" +
      '<h2 class="cas-title">' + esc(title) + "</h2></div></div>";

    nav.querySelectorAll(".cas-group").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var x = state.groups.find(function (y) { return y.key === btn.dataset.group; });
        select(firstUsable(x.parts[0].items).key);
      });
    });
    nav.querySelectorAll(".cas-part").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var x = g.parts.find(function (y) { return y.name === btn.dataset.part; });
        select(firstUsable(x.items).key);
      });
    });
    nav.querySelectorAll(".chip-book:not(.off)").forEach(function (btn) {
      btn.addEventListener("click", function () { select(btn.dataset.key); });
    });
  }

  function recHeadHTML() {
    var people = (state.data.picks && state.data.picks.recommenders) || [];
    return '<div class="rec-head"><span class="rec-head-label">추천자 ' + people.length + "명</span>" +
      people.map(function (p) {
        return '<span class="rec-person">' + esc(p.name) + "<small>" + esc([p.school, p.field].filter(Boolean).join(" · ")) + "</small></span>";
      }).join("") +
      '<span class="rec-more">신학교 교수님들의 추천을 모으고 있습니다. 자리는 비워 두었어요.</span></div>';
  }

  function renderList() {
    var where = locate(state.active);
    var featured = document.getElementById("featured");
    var podium = document.getElementById("podium");
    var list = document.getElementById("list");
    if (!where) { featured.innerHTML = ""; podium.innerHTML = ""; list.innerHTML = ""; return; }
    var color = where.item.color || where.part.color || where.group.color || "#5856d6";
    document.documentElement.style.setProperty("--sec", color);
    var books = where.item.books || [];
    featured.innerHTML = featuredHTML() + (PRODUCT === "picks" ? recHeadHTML() : "");
    podium.innerHTML = (books.length ? '<div class="podium">' + books.slice(0, 3).map(podiumHTML).join("") + "</div>" : "") +
      '<div id="podDetail" class="hidden"></div>';
    list.innerHTML = books.length
      ? books.slice(3).map(rowHTML).join("")
      : '<li class="row"><div class="byline">이번 주엔 해당하는 책이 없습니다.</div></li>';
  }

  function findBook(id) {
    var where = locate(state.active);
    return where ? (where.item.books || []).find(function (b) { return b.id === id; }) : null;
  }

  function bindExpand() {
    document.getElementById("list").addEventListener("click", function (e) {
      if (e.target.closest("a")) return;
      var top = e.target.closest(".row-top");
      if (top) top.parentElement.classList.toggle("open");
    });
    var podium = document.getElementById("podium");
    podium.addEventListener("click", function (e) {
      if (e.target.closest("a")) return;
      var pod = e.target.closest(".pod[data-id]");
      if (!pod) return;
      var panel = document.getElementById("podDetail");
      var wasOn = pod.classList.contains("on");
      podium.querySelectorAll(".pod.on").forEach(function (p) { p.classList.remove("on"); });
      if (wasOn) { panel.innerHTML = ""; panel.classList.add("hidden"); return; }
      var b = findBook(pod.dataset.id);
      if (!b) return;
      pod.classList.add("on");
      panel.innerHTML = '<div class="pod-detail"><div class="detail-title">' + esc(b.title) + "</div>" + detailHTML(b) + "</div>";
      panel.classList.remove("hidden");
    });
  }

  function renderChrome() {
    document.getElementById("weekLabel").textContent =
      state.data.weekLabel + (state.data.weeksTracked > 1 ? " · " + state.data.weeksTracked + "주 추적" : "");
    if (state.data.sample) document.getElementById("sampleBadge").classList.remove("hidden");
    var t = state.data.generatedAt ? state.data.generatedAt.replace("T", " ").slice(0, 16) : "";
    document.getElementById("footNote").innerHTML =
      '순위 산출: 교리니 공식 (<a href="method.html">방법론</a>) · 판매 데이터 출처: 알라딘 · ' + esc(t) + " 갱신" +
      (state.data.sample ? " · 지금 보이는 순위는 개발용 샘플입니다." : "");
  }

  function getJSON(url) {
    return fetch(url + "?v=" + Date.now()).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }

  Promise.all([getJSON("data.json"), getJSON("topics.json")]).then(function (res) {
    var data = res[0], topics = res[1];
    if (!data) throw new Error("data.json을 불러오지 못했습니다");
    state.data = data;
    state.groups = PRODUCT === "picks" ? buildPickGroups(data) : buildChartGroups(data, topics);
    var hashKey = (location.hash || "").slice(1);
    var start = (hashKey && locate(hashKey)) || null;
    if (!start || !(start.item.books || []).length) {
      var g0 = state.groups[0];
      start = { item: firstUsable(g0.parts[0].items) };
    }
    state.active = start.item.key;
    renderChrome();
    renderNav();
    renderList();
    bindExpand();
  }).catch(function (e) {
    document.getElementById("list").innerHTML =
      '<li class="row"><div class="byline">' + esc(e.message) + "</div></li>";
  });
})();

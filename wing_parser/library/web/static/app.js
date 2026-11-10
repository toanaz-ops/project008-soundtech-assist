"use strict";
/* Mixing knowledge library: single-page app. Export mode = data embedded in
   #library-data (read-only); server mode = JSON API with a PRJ012 bearer token. */
(function () {
  const TOKEN_KEY = "sb-abnbrulpqpyfisahdwen-auth-token";
  const embedded = document.getElementById("library-data");
  const EXPORT = !!embedded;
  const $ = (id) => document.getElementById(id);

  const TXT = {
    vi: {
      brand: "Thư viện Mix", search: "Tìm kiếm (không cần dấu)…", retired: "Hiện mục đã gỡ", newEntry: "+ Tạo mục",
      g_topic: "Chủ đề", g_instrument: "Nhạc cụ", g_genre: "Thể loại", g_technique: "Kỹ thuật", g_source: "Nguồn",
      none: "(chưa có)", empty: "Chọn một mục ở bên trái.", noMatch: "Không có mục nào khớp.", loading: "Đang tải…",
      summary: "Tóm tắt", sources: "Nguồn tham khảo", media: "Hình ảnh & video", unsourced: "THIẾU NGUỒN",
      unvetted: "NGUỒN CHƯA DUYỆT", layer_shipped: "bản gốc", layer_user: "đã chỉnh", edit: "Sửa", history: "Lịch sử",
      retire: "Gỡ mục", back: "Quay lại", rev: "bản", by: "bởi", licence: "giấy phép", credit: "tác giả",
      forbidden: "Tài khoản của bạn chưa được cấp quyền xem thư viện.", forbiddenHint: "Hãy liên hệ chủ hệ thống để được cấp quyền.",
      unavailable: "Dịch vụ xác thực tạm thời không khả dụng. Thử lại sau.", errorGeneric: "Có lỗi xảy ra",
      display: "Giao diện", language: "Ngôn ngữ", skin: "Giao diện màu", density: "Mật độ",
      lang_vi: "Tiếng Việt", lang_en: "English", skin_light: "Sáng", skin_dark: "Tối", skin_sodium: "Sodium Rack", skin_tet: "Tết",
      dens_comfortable: "Thoáng", dens_compact: "Gọn",
      exportNote: "Bản xuất chỉ đọc", save: "Lưu", cancel: "Huỷ", note: "Ghi chú thay đổi (bắt buộc)",
      f_id: "Mã (kebab-case, không đổi được)", f_title: "Tiêu đề (EN)", f_title_vi: "Tiêu đề (VI)", f_topic: "Chủ đề",
      f_tags: "Thẻ (cách nhau bằng dấu phẩy)", f_summary: "Tóm tắt (1-3 câu)", f_summary_vi: "Tóm tắt (VI)", f_body: "Nội dung (Markdown)",
      f_body_vi: "Nội dung (VI, Markdown)", m_caption_vi: "Chú thích (VI)", noVi: "Chưa có bản tiếng Việt — đang hiện bản tiếng Anh.", f_rule: "rule (JSON, tuỳ chọn)",
      f_conf: "Độ tin cậy", f_status: "Trạng thái", addSource: "+ Thêm nguồn", addMedia: "+ Thêm media", remove: "Xoá dòng",
      needSource: "Cần ít nhất một nguồn đầy đủ (tiêu đề, nhà xuất bản, loại, ngày truy cập, URL trừ sách).",
      needNote: "Cần ghi chú thay đổi.", badJson: "rule không phải JSON hợp lệ.", conflict: "Mục này vừa được người khác sửa. Tải lại rồi sửa lại.",
      exists: "Mã này đã tồn tại.", saved: "Đã lưu.", revisions: "Các bản", restore: "Khôi phục bản này", restoreAsk: "Khôi phục bản này thành bản mới?",
      retireAsk: "Gỡ mục này (có thể khôi phục từ lịch sử)? Nhập ghi chú:", baseline: "Bản đầu tiên, không có bản trước.",
      s_title: "Tiêu đề", s_publisher: "Nhà xuất bản", s_kind: "Loại", s_url: "URL", s_author: "Tác giả", s_year: "Năm",
      s_accessed: "Ngày truy cập", s_locator: "Vị trí (trang/mm:ss)", m_kind: "Loại", m_path: "Tệp", m_caption: "Chú thích",
      m_license: "Giấy phép", m_attribution: "Ghi công", m_channel: "Kênh", m_timestamp: "Mốc thời gian (mm:ss)", m_generated_by: "Tạo bởi",
      m_title: "Tiêu đề", validation: "Chưa hợp lệ:", watch: "Xem video", generated: "Xuất lúc"
    },
    en: {
      brand: "Mix library", search: "Search (diacritics optional)…", retired: "Show retired", newEntry: "+ New entry",
      g_topic: "Topic", g_instrument: "Instrument", g_genre: "Genre", g_technique: "Technique", g_source: "Source",
      none: "(none)", empty: "Pick an entry on the left.", noMatch: "No matching entries.", loading: "Loading…",
      summary: "Summary", sources: "Sources", media: "Images & video", unsourced: "UNSOURCED",
      unvetted: "UNVETTED SOURCE", layer_shipped: "shipped", layer_user: "edited", edit: "Edit", history: "History",
      retire: "Retire", back: "Back", rev: "rev", by: "by", licence: "licence", credit: "credit",
      forbidden: "Your account has not been granted access to the library.", forbiddenHint: "Ask the system owner for access.",
      unavailable: "The sign-in service is temporarily unavailable. Try again later.", errorGeneric: "Something went wrong",
      display: "Display", language: "Language", skin: "Skin", density: "Density",
      lang_vi: "Tiếng Việt", lang_en: "English", skin_light: "Light", skin_dark: "Dark", skin_sodium: "Sodium Rack", skin_tet: "Tet",
      dens_comfortable: "Comfortable", dens_compact: "Compact",
      exportNote: "Read-only export", save: "Save", cancel: "Cancel", note: "Change note (required)",
      f_id: "Id (kebab-case, fixed)", f_title: "Title (EN)", f_title_vi: "Title (VI)", f_topic: "Topic",
      f_tags: "Tags (comma separated)", f_summary: "Summary (1-3 sentences)", f_summary_vi: "Summary (VI)", f_body: "Body (Markdown)",
      f_body_vi: "Body (VI, Markdown)", m_caption_vi: "Caption (VI)", noVi: "", f_rule: "rule (JSON, optional)",
      f_conf: "Confidence", f_status: "Status", addSource: "+ Add source", addMedia: "+ Add media", remove: "Remove row",
      needSource: "At least one complete source is required (title, publisher, kind, accessed date, URL unless a book).",
      needNote: "A change note is required.", badJson: "rule is not valid JSON.", conflict: "Someone else just changed this entry. Reload and redo your edit.",
      exists: "That id already exists.", saved: "Saved.", revisions: "Revisions", restore: "Restore this version", restoreAsk: "Restore this version as a new revision?",
      retireAsk: "Retire this entry (it can be restored from history)? Enter a note:", baseline: "First revision, nothing before it.",
      s_title: "Title", s_publisher: "Publisher", s_kind: "Kind", s_url: "URL", s_author: "Author", s_year: "Year",
      s_accessed: "Accessed", s_locator: "Locator (page/mm:ss)", m_kind: "Kind", m_path: "File", m_caption: "Caption",
      m_license: "Licence", m_attribution: "Attribution", m_channel: "Channel", m_timestamp: "Timestamp (mm:ss)", m_generated_by: "Generated by",
      m_title: "Title", validation: "Not valid yet:", watch: "Watch video", generated: "Exported"
    }
  };

  const S = { lang: "vi", group: "topic", query: "", retired: false, id: null, data: null, canEdit: false,
              detail: {}, blobs: {} };
  const t = (k) => (TXT[S.lang] && TXT[S.lang][k]) || TXT.vi[k] || k;

  /* ---------- helpers ---------- */
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) {
      if (kid == null || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }
  const fold = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d").replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
  const lbl = (o) => (S.lang === "vi" && o.vi) || o.en || o.id;
  // Flatten nested arrays and drop false/null like h() does: `cond && node`
  // and `[heading, [figures]]` are passed straight in.
  const setView = (...nodes) => { const v = $("view"); v.replaceChildren(...nodes.flat(Infinity).filter((n) => n != null && n !== false)); v.scrollTop = 0; };
  // Plain hashes only (#e-<id>, #edit-<id>, #hist-<id>, #new): the artifact host passes just `#name`.
  const go = (kind, id) => { location.hash = kind === "new" ? "#new" : "#" + kind + "-" + id; };
  const safeHttp = (u) => /^https?:\/\//i.test(u || "") ? u : null;

  /* ---------- auth + API (server mode) ---------- */
  function toLogin() { location.href = "/login?next=" + encodeURIComponent(location.pathname); }
  function token() {
    let tok = null;
    try { tok = JSON.parse(localStorage.getItem(TOKEN_KEY) || "null"); } catch (e) { tok = null; }
    if (!tok || !tok.access_token || (tok.expires_at && tok.expires_at * 1000 <= Date.now() + 5000)) { toLogin(); throw new Error("login"); }
    return tok.access_token;
  }
  class ApiError extends Error { constructor(status, body) { super(status); this.status = status; this.body = body || {}; } }
  async function api(path, opts) {
    opts = opts || {};
    const headers = { Authorization: "Bearer " + token() };
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    const res = await fetch(path, { method: opts.method || "GET", headers, body: opts.body === undefined ? undefined : JSON.stringify(opts.body) });
    if (res.status === 401) { toLogin(); throw new Error("login"); }
    if (!res.ok) { let b = {}; try { b = await res.json(); } catch (e) { /* not json */ } throw new ApiError(res.status, b); }
    return opts.blob ? res.blob() : res.json();
  }
  function fatal(err) {
    if (err && err.message === "login") return;
    if (err instanceof ApiError && err.status === 403) {
      setView(h("div", { class: "center" }, h("h1", {}, t("brand")), h("p", {}, t("forbidden")), h("p", { class: "muted" }, t("forbiddenHint"))));
    } else if (err instanceof ApiError && (err.status === 503 || err.status === 502)) {
      setView(h("div", { class: "banner err" }, t("unavailable")));
    } else {
      setView(h("div", { class: "banner err" }, t("errorGeneric") + ": " + (err && err.message || err)));
    }
  }

  /* ---------- data ---------- */
  async function load() {
    if (EXPORT) { S.data = JSON.parse(embedded.textContent); S.canEdit = false; return; }
    S.data = await api("api/entries");
    S.canEdit = !!S.data.can_edit;
  }
  async function getDetail(id) {
    if (EXPORT) return S.data.entries.find((e) => e.id === id);
    if (!S.detail[id]) S.detail[id] = await api("api/entries/" + encodeURIComponent(id));
    return S.detail[id];
  }
  const topicLabel = (id) => { const tp = S.data.topics.find((x) => x.id === id); return tp ? lbl(tp) : id; };
  const viPick = (vi, en) => (S.lang === "vi" && vi) || en;
  const capOf = (m) => viPick(m.caption_vi, m.caption);
  const titleOf = (e) => (S.lang === "vi" && e.title_vi) || e.title;

  /* ---------- sidebar ---------- */
  function groupKeys(e) {
    const tags = e.tags || {};
    switch (S.group) {
      case "topic": return [e.topic];
      case "source": return e.publishers || [];
      default: return tags[S.group] || [];
    }
  }
  function filtered() {
    const tokens = fold(S.query).split(" ").filter(Boolean);
    const rows = S.data.entries.filter((e) => (S.retired || e.status !== "retired") &&
      tokens.every((tk) => e.folded_text.includes(tk)));
    const score = (e) => tokens.filter((tk) => e.folded_title.includes(tk)).length;
    return rows.sort((a, b) => score(b) - score(a) || titleOf(a).localeCompare(titleOf(b), S.lang));
  }
  function renderTree() {
    const rows = filtered();
    const groups = new Map();
    for (const e of rows) {
      const keys = groupKeys(e).filter(Boolean);
      for (const k of keys.length ? keys : [""]) {
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(e);
      }
    }
    const name = (k) => k === "" ? t("none") : S.group === "topic" ? topicLabel(k) : k;
    const sorted = [...groups.entries()].sort((a, b) => (a[0] === "") - (b[0] === "") || name(a[0]).localeCompare(name(b[0]), S.lang));
    const tree = $("tree");
    if (!rows.length) { tree.replaceChildren(h("p", { class: "muted" }, t("noMatch"))); return; }
    tree.replaceChildren(...sorted.map(([k, list]) => h("details", { open: !!S.query || list.some((e) => e.id === S.id) },
      h("summary", {}, name(k) + " ", h("span", { class: "n" }, "(" + list.length + ")")),
      list.map((e) => h("button", { type: "button", class: "item" + (e.id === S.id ? " sel" : "") + (e.status === "retired" ? " retired" : ""),
        onclick: () => { go("e", e.id); document.getElementById("app").classList.remove("menu-open"); } }, titleOf(e))))));
  }
  function renderChrome() {
    document.documentElement.lang = S.lang;
    $("q").placeholder = t("search");
    $("retired-label").textContent = t("retired");
    const gb = $("group-by");
    gb.replaceChildren(...["topic", "instrument", "genre", "technique", "source"].map((g) =>
      h("option", { value: g, selected: g === S.group }, t("g_" + g))));
    $("display-btn").textContent = t("display");
    renderDisplayMenu();
    const nb = $("new-btn");
    nb.hidden = !S.canEdit;
    nb.textContent = t("newEntry");
    document.querySelector(".brand").textContent = t("brand");
    document.title = t("brand");
  }

  /* ---------- entry view ---------- */
  function ytId(url) {
    try {
      const u = new URL(url);
      const host = u.hostname.replace(/^www\./, "");
      if (host === "youtu.be") return u.pathname.slice(1).split("/")[0];
      if (host === "youtube.com" || host === "m.youtube.com" || host === "youtube-nocookie.com") {
        if (u.pathname === "/watch") return u.searchParams.get("v");
        const m = u.pathname.match(/^\/(embed|shorts|live)\/([\w-]{6,})/);
        if (m) return m[2];
      }
    } catch (e) { /* not a url */ }
    return null;
  }
  function startSeconds(ts) {
    if (!ts) return 0;
    const p = String(ts).split(":").map(Number);
    if (p.some(isNaN)) return 0;
    return p.reduce((a, n) => a * 60 + n, 0);
  }
  function blobImg(src, alt) {
    const img = h("img", { alt: alt || "", loading: "lazy" });
    if (EXPORT) { img.src = src; return img; }
    (S.blobs[src] ? Promise.resolve(S.blobs[src]) : api(src, { blob: true }).then((b) => (S.blobs[src] = URL.createObjectURL(b))))
      .then((u) => { img.src = u; }).catch(() => { img.alt = "(image unavailable)"; });
    return img;
  }
  function sourceLine(s, i) {
    const bits = [s.publisher, s.kind, s.author, s.year, s.locator && ("§ " + s.locator), s.accessed && ("↗ " + s.accessed)].filter(Boolean).join(" · ");
    const url = safeHttp(s.url);
    return h("li", { id: "src-" + (i + 1) }, url ? h("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, s.title) : s.title,
      " — ", h("span", { class: "muted" }, bits));
  }
  function mediaBlocks(e) {
    const out = [];
    for (const m of e.media || []) {
      if (m.kind === "diagram" && m.src) {
        out.push(h("figure", {}, blobImg(m.src, capOf(m)), h("figcaption", {}, capOf(m) || "")));
      } else if (m.kind === "image") {
        const url = safeHttp(m.url);
        out.push(h("p", {}, "🖼 ", url ? h("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, capOf(m) || m.url) : (capOf(m) || ""),
          h("span", { class: "muted" }, " · " + t("licence") + " " + (m.license || "?") + " · " + t("credit") + " " + (m.attribution || "?"))));
      } else if (m.kind === "video") {
        const url = safeHttp(m.url), id = ytId(m.url || "");
        const block = h("div", { class: "video" });
        if (EXPORT) {
          // Iframes are blocked on the artifact host: a link card that opens YouTube in a new tab.
          const start = startSeconds(m.timestamp);
          const href = id ? "https://www.youtube.com/watch?v=" + encodeURIComponent(id) + (start ? "&t=" + start + "s" : "") : url;
          const label = ["▶ " + (m.title || "video"), m.channel, m.timestamp].filter(Boolean).join(" · ") + (capOf(m) ? " — " + capOf(m) : "");
          out.push(href ? h("a", { class: "video-card", href, target: "_blank", rel: "noopener noreferrer" }, label) : h("div", { class: "video-card" }, label));
          continue;
        }
        if (id) {
          const start = startSeconds(m.timestamp);
          block.append(h("iframe", { src: "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + (start ? "?start=" + start : ""),
            title: m.title || "video", loading: "lazy", referrerpolicy: "strict-origin-when-cross-origin", allowfullscreen: true,
            allow: "accelerometer; encrypted-media; gyroscope; picture-in-picture" }));
        }
        block.append(h("div", {}, "▶ ", url ? h("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, m.title) : m.title,
          h("span", { class: "muted" }, " · " + (m.channel || "") + (m.timestamp ? " · " + m.timestamp : "") + (capOf(m) ? " — " + capOf(m) : ""))));
        out.push(block);
      }
    }
    return out;
  }
  async function showEntry(id) {
    setView(h("p", { class: "muted" }, t("loading")));
    let e;
    try { e = await getDetail(id); } catch (err) { if (err instanceof ApiError && err.status === 404) e = null; else return fatal(err); }
    if (!e) return setView(h("div", { class: "banner" }, t("noMatch")));
    const badges = h("div", { class: "badges" },
      h("span", { class: "badge " + (e.confidence === "established" ? "ok" : e.confidence === "contested" ? "warn" : "") }, e.confidence),
      h("span", { class: "badge" + (e.status === "retired" ? " warn" : "") }, e.status),
      h("span", { class: "badge" }, t("layer_" + e.layer)),
      h("span", { class: "badge" }, topicLabel(e.topic)),
      e.unsourced && h("span", { class: "badge danger" }, t("unsourced")),
      e.unvetted && h("span", { class: "badge amber" }, t("unvetted")),
      ...["instrument", "genre", "technique"].flatMap((g) => ((e.tags || {})[g] || []).map((v) => h("span", { class: "badge" }, v))));
    const actions = (!EXPORT) && h("div", { class: "actions" },
      S.canEdit && h("button", { class: "btn", type: "button", onclick: () => go("edit", id) }, t("edit")),
      h("button", { class: "btn", type: "button", onclick: () => go("hist", id) }, t("history")),
      S.canEdit && e.status !== "retired" && h("button", { class: "btn danger", type: "button", onclick: () => retireEntry(id, e.revision) }, t("retire")));
    const media = mediaBlocks(e);
    const fallback = S.lang === "vi" && !(e.summary_vi && e.body_vi_html);
    setView(
      h("h1", {}, S.lang === "vi" ? titleOf(e) : e.title),
      S.lang === "vi" ? (e.title_vi && h("div", { class: "vi" }, e.title)) : (e.title_vi && h("div", { class: "vi" }, e.title_vi)),
      badges, actions,
      fallback && h("p", { class: "muted vi-note" }, t("noVi")),
      h("p", { class: "summary" }, viPick(e.summary_vi, e.summary)),
      h("div", { class: "body", html: viPick(e.body_vi_html, e.body_html) }),
      media.length ? [h("h2", {}, t("media")), media] : null,
      h("h2", {}, t("sources")),
      e.sources.length ? h("ol", { class: "src-list" }, e.sources.map(sourceLine)) : h("p", { class: "badge danger" }, t("unsourced")),
      h("p", { class: "muted" }, t("rev") + " " + e.revision + " · " + t("by") + " " + e.updated_by + " · " + e.updated_at));
    $("view").focus({ preventScroll: true });
  }
  function writeFail(err) {
    if (err instanceof ApiError && err.status === 422 && err.body && err.body.issues) {
      alert(t("validation") + "\n" + err.body.issues.map((i) => i.field + ": " + i.message).join("\n"));
    } else if (err instanceof ApiError && err.status === 409) alert(t("conflict"));
    else fatal(err);
  }
  async function retireEntry(id, revision) {
    if (EXPORT) return; // dialogs are no-ops on the artifact host; retiring is server-only
    const note = prompt(t("retireAsk"), "");
    if (note === null) return;
    try { await api("api/entries/" + id + "/retire", { method: "POST", body: { note, revision } }); await afterWrite(id); } catch (err) { writeFail(err); await afterWrite(id); }
  }
  async function afterWrite(id) {
    S.detail = {};
    await load();
    renderTree();
    if (location.hash === "#e-" + id) route(); else go("e", id);
  }

  /* ---------- edit form ---------- */
  const SRC_FIELDS = ["title", "publisher", "kind", "url", "author", "year", "accessed", "locator"];
  const MEDIA_FIELDS = ["kind", "path", "url", "title", "channel", "timestamp", "caption", "caption_vi", "license", "attribution", "generated_by"];
  function field(label, input) { return h("div", {}, h("label", {}, label), input); }
  function sel(options, value, extra) {
    return h("select", extra || {}, options.map((o) => h("option", { value: o, selected: o === value }, o)));
  }
  function rowCard(fields, values, kindOpts, prefix, onRemove) {
    const inputs = {};
    const grid = h("div", { class: "grid" });
    for (const f of fields) {
      const input = f === "kind" ? sel(kindOpts, values.kind || kindOpts[0]) :
        f === "license" && prefix === "m" ? h("input", { value: values[f] || "", list: "licences" }) : h("input", { value: values[f] == null ? "" : values[f] });
      inputs[f] = input;
      grid.append(field(t(prefix + "_" + f), input));
    }
    const card = h("div", { class: "card" }, grid, h("div", { class: "actions" },
      h("button", { type: "button", class: "btn danger", onclick: () => card.remove() }, t("remove"))));
    card.read = () => { const o = {}; for (const f of fields) { const v = inputs[f].value.trim(); if (v !== "") o[f] = (f === "year" && /^\d+$/.test(v)) ? Number(v) : v; } return o; };
    return card;
  }
  async function showForm(id) {
    if (!S.canEdit) return setView(h("div", { class: "banner err" }, t("forbidden")));
    const creating = !id;
    let e = { tags: {}, sources: [], media: [], confidence: "common-practice", status: "draft", topic: S.data.topics[0].id };
    if (!creating) { try { e = await getDetail(id); } catch (err) { return fatal(err); } }
    const sch = S.data.schema;
    const f = {
      id: h("input", { value: e.id || "", disabled: !creating, placeholder: "my-entry-id" }),
      title: h("input", { value: e.title || "" }), title_vi: h("input", { value: e.title_vi || "" }),
      topic: h("select", {}, S.data.topics.map((tp) => h("option", { value: tp.id, selected: tp.id === e.topic }, lbl(tp)))),
      summary: h("textarea", { rows: 3 }, e.summary || ""), body: h("textarea", { rows: 14 }, e.body || ""),
      summary_vi: h("textarea", { rows: 3 }, e.summary_vi || ""), body_vi: h("textarea", { rows: 14 }, e.body_vi || ""),
      rule: h("textarea", { rows: 4 }, e.rule ? JSON.stringify(e.rule, null, 2) : ""),
      confidence: sel(sch.confidence, e.confidence), status: sel(sch.status, e.status),
      note: h("input", { value: "" })
    };
    const tagInputs = {};
    const tagFields = sch.tag_keys.map((k) => { tagInputs[k] = h("input", { value: ((e.tags || {})[k] || []).join(", ") }); return field(k, tagInputs[k]); });
    const srcBox = h("div", {}), mediaBox = h("div", {});
    const addSrc = (s) => srcBox.append(rowCard(SRC_FIELDS, s || { accessed: new Date().toISOString().slice(0, 10) }, sch.source_kinds, "s"));
    const addMedia = (m) => mediaBox.append(rowCard(MEDIA_FIELDS, m || {}, sch.media_kinds, "m"));
    (e.sources || []).forEach(addSrc); if (!(e.sources || []).length) addSrc();
    (e.media || []).forEach(addMedia);
    const msg = h("div", {});
    const lic = h("datalist", { id: "licences" }, sch.image_licenses.map((l) => h("option", { value: l })));
    const collect = () => {
      const split = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
      const entry = { id: f.id.value.trim(), title: f.title.value.trim(), topic: f.topic.value, summary: f.summary.value.trim(),
        body: f.body.value, confidence: f.confidence.value, status: f.status.value,
        tags: Object.fromEntries(sch.tag_keys.map((k) => [k, split(tagInputs[k].value)])),
        sources: [...srcBox.children].map((c) => c.read()), media: [...mediaBox.children].map((c) => c.read()) };
      if (f.title_vi.value.trim()) entry.title_vi = f.title_vi.value.trim();
      if (f.summary_vi.value.trim()) entry.summary_vi = f.summary_vi.value.trim();
      if (f.body_vi.value.trim()) entry.body_vi = f.body_vi.value;
      if (f.rule.value.trim()) entry.rule = JSON.parse(f.rule.value);
      return entry;
    };
    const problems = (entry) => {
      const out = [];
      const okSrc = entry.sources.some((s) => s.title && s.publisher && s.kind && s.accessed && (s.url || s.kind === "book"));
      if (!okSrc) out.push(t("needSource"));
      if (!f.note.value.trim() && !creating) out.push(t("needNote"));
      return out;
    };
    const submit = async () => {
      msg.replaceChildren();
      let entry;
      try { entry = collect(); } catch (err) { msg.append(h("div", { class: "banner err" }, t("badJson"))); return; }
      const errs = problems(entry);
      if (errs.length) { msg.append(h("div", { class: "banner err" }, errs.map((x) => h("div", {}, x)))); return; }
      try {
        const body = { entry, note: f.note.value.trim() };
        const saved = creating ? await api("api/entries", { method: "POST", body }) :
          await api("api/entries/" + id, { method: "PUT", body: { ...body, revision: e.revision } });
        await afterWrite(saved.id);
      } catch (err) {
        if (err instanceof ApiError && err.status === 422 && err.body.issues) {
          msg.append(h("div", { class: "banner err" }, t("validation"), h("ul", { class: "issues" },
            err.body.issues.map((i) => h("li", { class: i.level }, i.field + ": " + i.message)))));
        } else if (err instanceof ApiError && err.status === 409) {
          msg.append(h("div", { class: "banner err" }, err.body.detail === "exists" ? t("exists") : t("conflict")));
        } else fatal(err);
      }
    };
    setView(h("form", { class: "form", onsubmit: (ev) => { ev.preventDefault(); submit(); } },
      h("h1", {}, creating ? t("newEntry") : t("edit") + ": " + e.title),
      field(t("f_id"), f.id), field(t("f_title"), f.title), field(t("f_title_vi"), f.title_vi), field(t("f_topic"), f.topic),
      h("div", { class: "grid" }, tagFields), field(t("f_summary"), f.summary), field(t("f_summary_vi"), f.summary_vi),
      field(t("f_body"), f.body), field(t("f_body_vi"), f.body_vi),
      h("div", { class: "grid" }, field(t("f_conf"), f.confidence), field(t("f_status"), f.status)),
      h("h2", {}, t("sources")), srcBox, h("button", { type: "button", class: "btn", onclick: () => addSrc() }, t("addSource")),
      h("h2", {}, t("media")), mediaBox, h("button", { type: "button", class: "btn", onclick: () => addMedia() }, t("addMedia")),
      field(t("f_rule"), f.rule), field(t("note"), f.note), lic, msg,
      h("div", { class: "actions" }, h("button", { type: "submit", class: "btn primary" }, t("save")),
        h("button", { type: "button", class: "btn", onclick: () => (creating ? (location.hash = "") : go("e", id)) }, t("cancel")))));
  }

  /* ---------- history ---------- */
  function diffNode(text) {
    return h("pre", { class: "diff" }, text.split("\n").map((ln) => h("span", { class: ln.startsWith("@@") ? "hunk" : ln.startsWith("+") && !ln.startsWith("+++") ? "add" : ln.startsWith("-") && !ln.startsWith("---") ? "del" : "" }, ln + "\n")));
  }
  async function showHistory(id) {
    let revs;
    try { revs = (await api("api/entries/" + id + "/history")).revisions; } catch (err) { return fatal(err); }
    const diffBox = h("div", {}), list = h("div", {});
    const pick = async (i) => {
      [...list.children].forEach((c, j) => c.classList.toggle("sel", j === i));
      if (i === 0) { diffBox.replaceChildren(h("p", { class: "muted" }, t("baseline"))); return; }
      try { diffBox.replaceChildren(diffNode((await api("api/entries/" + id + "/diff?a=" + revs[i - 1].rev + "&b=" + revs[i].rev)).diff)); } catch (err) { fatal(err); }
    };
    revs.forEach((r, i) => list.append(h("div", { class: "rev", onclick: () => pick(i) },
      h("strong", {}, "r" + r.rev), h("span", { class: "badge" }, r.action), h("span", {}, r.note),
      h("span", { class: "muted" }, r.author + " · " + r.at),
      S.canEdit && h("button", { type: "button", class: "btn", onclick: async (ev) => {
        ev.stopPropagation();
        if (EXPORT || !confirm(t("restoreAsk"))) return;
        try { await api("api/entries/" + id + "/restore", { method: "POST", body: { rev: r.rev, note: "", revision: revs[revs.length - 1].rev } }); await afterWrite(id); } catch (err) { writeFail(err); }
      } }, t("restore")))));
    setView(h("h1", {}, t("history") + ": " + id), h("div", { class: "actions" }, h("button", { class: "btn", type: "button", onclick: () => go("e", id) }, t("back"))),
      h("h2", {}, t("revisions")), list, diffBox);
    if (revs.length) pick(revs.length - 1);
  }

  /* ---------- routing ---------- */
  function route() {
    // Plain form #e-<id>; the old #/e/<id> form still resolves.
    const m = location.hash.match(/^#(?:\/(e|edit|hist)\/|(edit|hist|e)-)([\w-]+)$/);
    if (m) { m[1] = m[1] || m[2]; m[2] = m[3]; }
    const isNew = location.hash === "#new" || location.hash === "#/new";
    S.id = m && m[1] === "e" ? m[2] : (m ? m[2] : null);
    renderTree();
    if (m && m[1] === "e") showEntry(m[2]);
    else if (m && m[1] === "edit") showForm(m[2]);
    else if (m && m[1] === "hist" && !EXPORT) showHistory(m[2]);
    else if (isNew) showForm(null);
    else setView(h("p", { class: "muted" }, t("empty")), EXPORT && h("p", { class: "muted" }, t("exportNote") + " · " + t("generated") + " " + (S.data.generated_at || "")));
  }
  // -- display prefs, shared with the PRJ012 app (same origin): az.prefs.v1 {skin, density} + az.language -------------------
  const SKINS = ["light", "dark", "sodium", "tet"], DENSITIES = ["comfortable", "compact"], LANGS = ["vi", "en"];
  const PREFS_KEY = "az.prefs.v1", LANG_KEY = "az.language";
  const P = { skin: "light", density: "compact" };
  function readPrefs() {
    let skin = "light", density = "compact", lang = "vi";
    try {
      const p = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}");
      if (p && SKINS.includes(p.skin)) skin = p.skin;
      if (p && DENSITIES.includes(p.density)) density = p.density;
    } catch (e) { /* storage blocked or bad JSON: defaults */ }
    try {
      const g = localStorage.getItem(LANG_KEY);
      if (LANGS.includes(g)) lang = g;
      else { const old = localStorage.getItem("library-lang"); if (LANGS.includes(old)) lang = old; }
    } catch (e) { /* defaults */ }
    P.skin = skin; P.density = density; S.lang = lang;
  }
  function applyPrefs() {
    const d = document.documentElement;
    d.setAttribute("data-skin", P.skin); d.setAttribute("data-density", P.density); d.lang = S.lang;
  }
  function savePrefs() {
    try {  // merge: keep keys the app may store alongside ours
      let p = {};
      try { p = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}"); } catch (e) { p = {}; }
      if (!p || typeof p !== "object" || Array.isArray(p)) p = {};
      p.skin = P.skin; p.density = P.density;
      localStorage.setItem(PREFS_KEY, JSON.stringify(p));
      localStorage.setItem(LANG_KEY, S.lang);
    } catch (e) { /* private mode */ }
  }
  function setPref(kind, value) {
    if (kind === "lang") S.lang = value; else P[kind] = value;
    applyPrefs(); savePrefs(); renderChrome(); route();
  }
  function renderDisplayMenu() {
    const menu = $("display-menu");
    const group = (title, cls, kind, values, cur, key) => [
      h("h3", {}, t(title)),
      h("div", { role: "group", "aria-label": t(title), class: cls }, values.map((v) =>
        h("button", { type: "button", class: kind === "skin" ? "skin-swatch" : "chip-toggle", "aria-pressed": String(cur === v),
          "data-value": v, onclick: () => setPref(kind, v) }, t(key + v))))];
    menu.setAttribute("aria-label", t("display"));
    const active = document.activeElement, keep = menu.contains(active) && active.dataset ? active.dataset.value : null;
    menu.replaceChildren(...group("language", "lang-switcher", "lang", LANGS, S.lang, "lang_"),
      ...group("skin", "skin-picker", "skin", SKINS, P.skin, "skin_"),
      ...group("density", "role-switcher", "density", DENSITIES, P.density, "dens_"));
    if (keep) { const again = menu.querySelector('[data-value="' + keep + '"]'); if (again) again.focus(); }
  }
  function wireDisplayMenu() {
    const btn = $("display-btn"), menu = $("display-menu");
    const setOpen = (open, refocus) => {
      menu.hidden = !open; btn.setAttribute("aria-expanded", String(open));
      if (open) { const first = menu.querySelector("button"); if (first) first.focus(); }
      else if (refocus) btn.focus();
    };
    btn.addEventListener("click", () => setOpen(menu.hidden));
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !menu.hidden) { ev.preventDefault(); setOpen(false, true); } });
    document.addEventListener("click", (ev) => { const path = ev.composedPath(); /* chips re-render on click, so test the dispatch-time path */
      if (!menu.hidden && !path.includes(menu) && !path.includes(btn)) setOpen(false, false); });
    // A change made in the PRJ012 app (another tab) updates this page live.
    window.addEventListener("storage", (ev) => {
      if (ev.key !== null && ev.key !== PREFS_KEY && ev.key !== LANG_KEY) return;
      const before = S.lang;
      readPrefs(); applyPrefs(); renderChrome();
      if (S.lang !== before) route();
    });
  }
  function wire() {
    $("q").addEventListener("input", (ev) => { S.query = ev.target.value; renderTree(); });
    $("group-by").addEventListener("change", (ev) => { S.group = ev.target.value; renderTree(); });
    $("show-retired").addEventListener("change", (ev) => { S.retired = ev.target.checked; renderTree(); });
    wireDisplayMenu();
    $("new-btn").addEventListener("click", () => go("new"));
    $("menu-btn").addEventListener("click", () => $("app").classList.toggle("menu-open"));
    window.addEventListener("hashchange", route);
  }
  (async function main() {
    readPrefs();
    applyPrefs();
    wire();
    renderChrome();
    setView(h("p", { class: "muted" }, t("loading")));
    try { await load(); } catch (err) { return fatal(err); }
    renderChrome();
    route();
  })();
})();

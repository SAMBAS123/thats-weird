(function () {
  const $ = (id) => document.getElementById(id);

  function fmtNum(n) {
    if (n === null || n === undefined || n === "") return "—";
    return Number(n).toLocaleString("en-US");
  }

  function shortDate(iso) {
    if (!iso) return "";
    const d = String(iso).slice(0, 10);
    return d.slice(5).replace("-", "·");
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function docketRow(item) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.className = "row";
    a.href = item.url || "#";
    if (item.url) {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    a.appendChild(el("time", null, shortDate(item.date_filed)));
    const body = el("div");
    body.appendChild(el("span", "title", item.case_name || "Untitled"));
    const meta = [item.docket_number, item.court].filter(Boolean).join(" · ");
    body.appendChild(el("span", "outlet", meta));
    a.appendChild(body);
    li.appendChild(a);
    return li;
  }

  function newsRow(item) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.className = "row";
    a.href = item.url || "#";
    if (item.url) {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    a.appendChild(el("time", null, shortDate(item.published)));
    const body = el("div");
    body.appendChild(el("span", "title", item.title || ""));
    if (item.outlet) body.appendChild(el("span", "outlet", item.outlet));
    a.appendChild(body);
    li.appendChild(a);
    return li;
  }

  function recordChip(item) {
    const a = document.createElement("a");
    a.className = "chip";
    a.href = item.url || "#";
    if (item.url) {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    const left = el("div");
    left.appendChild(el("b", null, item.value || ""));
    left.appendChild(el("small", null, item.period || ""));
    const right = el("div");
    right.appendChild(el("span", "title", item.label || ""));
    right.appendChild(el("span", "outlet", item.source || ""));
    a.appendChild(left);
    a.appendChild(right);
    return a;
  }

  function render(tape) {
    const d = tape.dockets || {};
    const n = tape.news || {};
    $("total").textContent = fmtNum(d.total);
    $("d7").textContent = fmtNum(d.filed_7d);
    $("d30").textContent = fmtNum(d.filed_30d);
    $("n7").textContent = fmtNum(n.hits_7d);
    $("checked").textContent = tape.as_of
      ? "last checked " + tape.as_of.replace("T", " ").replace("Z", " UTC")
      : "";

    if (d.search_url) $("cl-link").href = d.search_url;

    const dockets = $("dockets");
    dockets.replaceChildren();
    (d.latest || []).slice(0, 6).forEach((item) => dockets.appendChild(docketRow(item)));

    const news = $("news");
    news.replaceChildren();
    (n.latest || []).slice(0, 6).forEach((item) => news.appendChild(newsRow(item)));

    const record = $("record");
    record.replaceChildren();
    (tape.record || []).forEach((item) => record.appendChild(recordChip(item)));

    const token = tape.token;
    $("token-line").textContent = token
      ? "ticker " + (token.symbol || "token") + " · " + (token.mint || "")
      : "no ticker yet";

    if (tape.errors && tape.errors.length) {
      $("status").className = "status err";
      $("status").textContent = "partial tape: " + tape.errors.join(" · ");
    } else {
      $("status").className = "status";
      $("status").textContent = "";
    }
  }

  fetch("tape.json", { cache: "no-store" })
    .then((res) => {
      if (!res.ok) throw new Error("tape " + res.status);
      return res.json();
    })
    .then(render)
    .catch((err) => {
      $("checked").textContent = "could not load tape.json";
      $("status").className = "status err";
      $("status").textContent = String(err.message || err);
    });
})();

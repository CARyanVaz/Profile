/* Vaz & Associates: Piju, the site assistant (vanilla JS, no dependencies).
   Runs entirely in the visitor's browser and only repeats answers published on this site
   and reel captions reviewed by Ryan (assets/data/chatbot.json, built by tools/build_chatbot.py). It uses no AI service,
   writes nothing of its own, and sends what is typed nowhere unless the visitor chooses
   to pass it on by WhatsApp. Loaded by js/main.js when the assistant is first opened. */
window.VazChatbot = (function () {
  "use strict";
  var WA = "https://wa.me/916366446161?text=";
  var STOP = {};
  ("a an and any are as at be but by can could do does for from get give had has have how i if in into is it its me my need "
    + "of on or our please should so tell than that the their them then there these this to was we what when where which who why "
    + "will with would you your about am been being did doing having him her know like more much no not only other some such want very ok hi hello").split(" ")
    .forEach(function (w) { STOP[w] = 1; });
  var SYNONYMS = {
    itr: "income tax return", gstin: "gst registration", nonresident: "nri", accountant: "chartered accountant",
    ca: "chartered accountant", society: "housing society", cooperative: "housing society", bookkeeping: "accounts",
    accounting: "accounts", cfo: "cfo finance", fraud: "forensic", investigation: "forensic", mis: "reporting",
    automate: "automation", script: "apps script automation", macro: "automation", vba: "automation", python: "automation",
    website: "web design", calculator: "calculators tools", calculate: "calculators tools", deadline: "due date",
    duedate: "due date", overseas: "international nri", abroad: "international nri", property: "property house",
    arrested: "arrest", arrests: "arrest", cancelled: "cancellation", cancel: "cancellation", cancelling: "cancellation",
    filed: "file", filing: "file return", registered: "registration", register: "registration", replying: "reply", replied: "reply",
    appealing: "appeal", eway: "e way bill", dubai: "gulf international", uae: "gulf international", singapore: "international", flat: "property house", house: "property house", mismatch: "reconciliation", reco: "reconciliation"
  };

  function stem(w) {
    if (w.length > 4 && /ies$/.test(w)) return w.slice(0, -3) + "y";
    if (w.length > 3 && /s$/.test(w) && !/(ss|us|is)$/.test(w)) return w.slice(0, -1);
    return w;
  }
  function words(text) {
    return String(text).toLowerCase().replace(/[’']s\b/g, "").replace(/non[- ]resident/g, "nonresident")
      .replace(/co-?operative/g, "cooperative").replace(/[^a-z0-9]+/g, " ").trim().split(" ")
      .filter(function (w) { return w && !STOP[w]; }).map(stem);
  }

  /* Weighted keyword search over published answers. Returns matches, best first. */
  function makeIndex(entries) {
    var df = {};
    var docs = entries.map(function (e) {
      var q = {}, all = {};
      words(e.q).forEach(function (w) { q[w] = 1; all[w] = 1; });
      words(e.a).forEach(function (w) { all[w] = 1; });
      Object.keys(all).forEach(function (w) { df[w] = (df[w] || 0) + 1; });
      return { e: e, q: q, all: all };
    });
    var N = docs.length;
    var RANK = { faq: 1.25, page: 1, summary: 0.9, local: 0.8, reel: 1 };
    function idf(w) { return Math.log(1 + N / ((df[w] || 0) + 0.5)); }
    return function search(text) {
      var original = words(text);
      var asksAboutService = /\b(do|can|does|will) (you|ryan|the firm)\b|\bservices?\b|\boffer\b|\bprovide\b|\bhandle\b/i.test(text);
      if (!original.length) return [];
      var known = original.filter(function (w) { return df[w]; });
      var seen = {}, terms = [];
      original.forEach(function (w) {
        var alts = [w].concat(SYNONYMS[w] ? words(SYNONYMS[w]) : []);
        alts.forEach(function (t) { if (!seen[t] && df[t]) { seen[t] = 1; terms.push({ t: t, root: w }); } });
      });
      var total = 0, weightOf = {};
      original.forEach(function (w) {
        var best = idf(w);
        (SYNONYMS[w] ? words(SYNONYMS[w]) : []).forEach(function (t) { if (df[t]) best = Math.max(best, idf(t)); });
        weightOf[w] = best; total += best;
      });
      var results = [];
      docs.forEach(function (d) {
        var score = 0, inQ = {}, inAny = {};
        terms.forEach(function (x) {
          if (d.q[x.t]) { score += 3 * idf(x.t); inQ[x.root] = 1; inAny[x.root] = 1; }
          else if (d.all[x.t]) { score += idf(x.t); inAny[x.root] = 1; }
        });
        if (!score) return;
        var covered = 0, coveredQ = 0;
        original.forEach(function (w) {
          if (inAny[w]) covered += weightOf[w];
          if (inQ[w]) coveredQ += weightOf[w];
        });
        var share = covered / total;
        /* Most of the question must be covered, or the assistant passes it to Ryan rather than guess. */
        if (share < 0.55 || !(coveredQ / total >= 0.34)) return;
        var offer = asksAboutService && d.e.k === "summary" ? 1.6 : 1;
        var named = original.some(function (w) { return w.length > 3 && d.e.u.split("#")[0].indexOf(w) >= 0; }) ? 1.3 : 1;
        results.push({ e: d.e, score: score * (0.5 + share) * (0.4 + coveredQ / total) * RANK[d.e.k] * offer * named });
      });
      results.sort(function (a, b) { return b.score - a.score; });
      return known.length ? results : [];
    };
  }

  var FIXED = [
    { re: /^(hi|hello|hey|namaste|good (morning|afternoon|evening))\b[\s.!]*$/i,
      text: "Hello. Type a question, or choose a subject from the menu." , menu: true },
    { re: /^(thanks?|thank you|ok|okay|fine|great)\b[\s.!]*$/i,
      text: "You are welcome. If your question needs more detail, Ryan can take it up with you directly.", wa: true },
    { re: /\b(are you|is this) (a |an )?(bot|human|real|person|ai|robot|chatbot)\b|\bwho are you\b|\b(what is|what's) your name\b|\b(who|what) is piju\b|^piju\b[\s?.!]*$/i,
      text: "I am Piju, an automated assistant. I repeat answers published on this website and do not replace advice from Ryan Vaz, FCA.", wa: true },
    { re: /\b(talk|speak|call|meet|connect|contact|reach)\b.*\b(ryan|ca|someone|person|you|human|office|firm)\b|\bcontact (details|number)\b|\b(phone|mobile|whatsapp|email|e-mail)\b|^contact\b/i,
      text: "You can reach Ryan Vaz by phone or WhatsApp on +91 63664 46161, or by email at ryan@vazassociates.in. The contact page has a form too.", link: ["/contact/", "Contact page"], wa: true },
    { re: /\b(where|address|location|located|office|directions?|timings?|hours|open)\b.*\b(you|your|office|firm|ryan)\b|^(address|location|office)\b|\byour (address|office|location|timings?|hours)\b/i,
      text: "The practice is in Borivali West, Mumbai. Meetings are by appointment, so please confirm a time with Ryan first.", link: ["/ca-borivali-west/", "Borivali West office"], wa: true },
    { re: /\b(your|ryan'?s?|you) (fee|fees|charge|charges|rates?|pricing|price)\b|\b(do|will) you charge\b|\bhow much (do|will|would|does|is) (you|it|that|this)( cost| charge)?\b|^(fees?|charges?|pricing|prices?|quote|rates)\b[\s?.!]*$|\bwhat (are|is) (the )?(fees?|charges?)\b[\s?.!]*$/i,
      text: "Fees are not published on this website. They depend on the scope of work and are agreed with Ryan directly before work begins.", wa: true }
  ];
  /* Topic buttons: label, then the question it asks. CA services first, income tax and GST separate. */
  var CHIPS = [
    ["Income tax notice", "I received an income tax notice"],
    ["Late income tax return", "Can I still file my return after the due date"],
    ["GST registration", "When is GST registration mandatory"],
    ["GST refund", "Will GST refunds now be paid faster"],
    ["NRI selling property", "What tax is deducted when an NRI sells property"],
    ["Audit", "Audit and assurance services"],
    ["Housing society", "Co-operative housing society accounting and audit"],
    ["Due dates", "Compliance calendar due dates"],
    ["Tax calculators", "Tax calculators"],
    ["Finance automation", "Finance automation services"]
  ];

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  function create(opts) {
    var base = opts.base, track = opts.track, launcher = opts.launcher;
    var search = null, loading = null, lastQuestion = "", menu = null, entries = [];
    var topic = (document.querySelector("h1") || {}).textContent;

    var panel = el("div", "cb-panel");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Piju, site assistant");
    panel.hidden = true;
    var head = el("div", "cb-head");
    var heading = el("div");
    heading.appendChild(el("p", "cb-title", "Piju"));
    var subtitle = el("p", "cb-sub", "Automated assistant. Answers from this website only.");
    heading.appendChild(subtitle);
    var close = el("button", "cb-close");
    close.type = "button";
    close.setAttribute("aria-label", "Close Piju");
    close.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    head.appendChild(heading); head.appendChild(close);
    var log = el("div", "cb-log");
    log.setAttribute("role", "log");
    log.setAttribute("aria-live", "polite");
    log.tabIndex = 0;
    var form = el("form", "cb-form");
    var label = el("label", "cb-sr", "Your question");
    label.htmlFor = "cb-input";
    var input = el("input", "cb-input");
    input.id = "cb-input"; input.type = "text"; input.maxLength = 300; input.autocomplete = "off";
    input.placeholder = "Type your question";
    var send = el("button", "cb-send", "Ask");
    send.type = "submit";
    form.appendChild(label); form.appendChild(input); form.appendChild(send);
    var note = el("p", "cb-note", "General information, not professional advice. Please do not type PAN, Aadhaar or account details.");
    panel.appendChild(head); panel.appendChild(log); panel.appendChild(form); panel.appendChild(note);
    document.body.appendChild(panel);

    function url(path) { return /^https:/.test(path) ? path : base + path.replace(/^\//, ""); }
    function reelLink(e) {
      var a = el("a", "cb-link", "Watch the " + e.t);
      a.href = e.u; a.target = "_blank"; a.rel = "noopener";
      return a;
    }
    /* The newest reel among those that match the question about as well as the best one. */
    function newestReel(reels) {
      return reels.filter(function (h) { return h.score >= reels[0].score * 0.6; })
        .sort(function (x, y) { return x.e.d < y.e.d ? 1 : -1; })[0].e;
    }
    function waLink(question) {
      var msg = question ? "Hello Ryan, I have a query: " + question
        : "Hello Ryan, I have a query" + (topic ? " (from your page: " + topic.replace(/\s+/g, " ").trim() + ")" : "") + ".";
      var a = el("a", "cb-wa", "Ask Ryan on WhatsApp");
      a.href = WA + encodeURIComponent(msg); a.target = "_blank"; a.rel = "noopener";
      return a;
    }
    function scroll(node) {
      log.scrollTop = node ? node.offsetTop - log.offsetTop - 8 : log.scrollHeight;
    }
    function bubble(text, who) {
      var b = el("div", "cb-msg cb-" + who);
      if (text) b.appendChild(el("p", "", text));
      log.appendChild(b);
      return b;
    }
    function chipRow(items) {
      var row = el("div", "cb-chips");
      items.forEach(function (t) {
        var pair = typeof t === "string" ? [t, t] : t;
        var c = el("button", "cb-chip", pair[0]);
        c.type = "button";
        c.addEventListener("click", function () { ask(pair[1], pair[0]); });
        row.appendChild(c);
      });
      return row;
    }
    /* The menu: subject, then activity, then question. Built from assets/data/chatbot.json. */
    function menuRow(items) {
      var row = el("div", "cb-menu");
      items.forEach(function (it) {
        var c = el(it.href ? "a" : "button", "cb-menu-item" + (it.nav ? " cb-menu-nav" : ""), it.label);
        if (it.href) { c.href = url(it.href); }
        else { c.type = "button"; c.addEventListener("click", function () { it.go(it); }); }
        row.appendChild(c);
      });
      log.appendChild(row);
      return row;
    }
    function pick(label, draw, id) {
      var mine = bubble(label, "me");
      if (id) track("chatbot_menu", { item: id });
      draw();
      scroll(mine);
    }
    function homeNav() { return { label: "Main menu", nav: true, go: function () { pick("Main menu", showSubjects); } }; }
    function showSubjects() {
      bubble("Choose a subject.", "bot");
      menuRow(menu.map(function (a) {
        return { label: a.label, go: function () { pick(a.label, function () { showActivities(a); }, a.id); } };
      }));
    }
    function showActivities(a) {
      if (a.subs.length === 1) { showQuestions(a, a.subs[0]); return; }
      bubble(a.label + ": choose an activity.", "bot");
      menuRow(a.subs.map(function (s) {
        return { label: s.label, go: function () { pick(s.label, function () { showQuestions(a, s); }, s.id); } };
      }).concat([homeNav()]));
    }
    function backNav(a) {
      return { label: "Back to " + a.label, nav: true, go: function () { pick("Back to " + a.label, function () { showActivities(a); }); } };
    }
    function showQuestions(a, s) {
      bubble(a.subs.length === 1 ? a.label + ": choose a question." : s.label + ": choose a question.", "bot");
      var rows = entries.filter(function (e) { return e.m === s.id; }).map(function (e) {
        return { label: e.q, go: function () { pick(e.q, function () { showAnswer(a, s, e); }, s.id); } };
      });
      s.links.forEach(function (l) { rows.push({ label: l[0], href: l[1] }); });
      if (a.subs.length > 1) rows.push(backNav(a));
      rows.push(homeNav());
      menuRow(rows);
    }
    function showAnswer(a, s, e) {
      var b = bubble(e.a, "bot");
      var more = el("a", "cb-link", "Read on: " + e.t);
      more.href = url(e.u);
      b.appendChild(more);
      b.appendChild(waLink(e.q));
      var nav = [{ label: "More on " + s.label, nav: true, go: function () { pick("More on " + s.label, function () { showQuestions(a, s); }); } }];
      nav.push(homeNav());
      menuRow(nav);
    }
    function reply(question) {
      for (var i = 0; i < FIXED.length; i++) {
        if (FIXED[i].re.test(question)) {
          var f = FIXED[i], fb = bubble(f.text, "bot");
          if (f.link) {
            var fl = el("a", "cb-link", f.link[1]);
            fl.href = url(f.link[0]);
            fb.appendChild(fl);
          }
          if (f.wa) fb.appendChild(waLink(f.wa === true ? "" : question));
          if (f.menu && menu) menuRow([homeNav()]);
          track("chatbot_question", { matched: true });
          return fb;
        }
      }
      var all = search(question);
      var reels = all.filter(function (h) { return h.e.k === "reel"; });
      var hits = all.filter(function (h) { return h.e.k !== "reel"; });
      track("chatbot_question", { matched: all.length > 0 });
      /* Published answers come first. A reel's caption is the answer only when nothing else matches. */
      if (!hits.length && reels.length) {
        var re = newestReel(reels), rb = bubble(re.a, "bot");
        rb.appendChild(reelLink(re));
        rb.appendChild(waLink(question));
        return rb;
      }
      if (!hits.length) {
        var nb = bubble("I could not find this on the website. Ryan can answer it directly.", "bot");
        nb.appendChild(waLink(question));
        return nb;
      }
      var top = hits[0].e, b = bubble(top.a, "bot");
      var more = el("a", "cb-link", "Read on: " + top.t);
      more.href = url(top.u);
      b.appendChild(more);
      if (reels.length) b.appendChild(reelLink(newestReel(reels)));
      b.appendChild(waLink(question));
      var seen = {}; seen[top.q] = 1;
      var related = [];
      hits.slice(1).forEach(function (h) {
        if (related.length < 2 && !seen[h.e.q] && h.e.k !== "summary" && h.score > hits[0].score * 0.45) {
          seen[h.e.q] = 1; related.push(h.e.q);
        }
      });
      if (related.length) log.appendChild(chipRow(related));
      return b;
    }
    function ask(question, shown) {
      question = question.replace(/\s+/g, " ").trim();
      if (!question) return;
      lastQuestion = question;
      var mine = bubble(shown || question, "me");
      input.value = "";
      load().then(function () {
        reply(question);
        if (menu && !FIXED.some(function (f) { return f.menu && f.re.test(question); })) menuRow([homeNav()]);
        scroll(mine);
      }, function () {
        var b = bubble("The answers could not be loaded just now. Ryan can answer directly.", "bot");
        b.appendChild(waLink(lastQuestion));
        scroll(mine);
      });
    }
    function load() {
      if (!loading) {
        loading = fetch(url("assets/data/chatbot.json"))
          .then(function (r) { if (!r.ok) throw new Error("load"); return r.json(); })
          .then(function (d) {
            search = makeIndex(d.entries);
            entries = d.entries;
            menu = d.menu && d.menu.length ? d.menu : null;
            if (d.entries.some(function (e) { return e.k === "reel"; })) subtitle.textContent = "Automated assistant. Answers from this website and Ryan's reels.";
          })
          .catch(function (err) { loading = null; throw err; });
      }
      return loading;
    }
    function show(open) {
      panel.hidden = !open;
      document.documentElement.classList.toggle("cb-open", open);
      if (open) input.focus(); else launcher.focus();
    }

    var hello = bubble("Hello, I am Piju. I can find answers published on this website. Choose from the menu, or type your question below.", "bot");
    hello.appendChild(waLink(""));
    load().then(function () {
      if (menu) showSubjects(); else log.appendChild(chipRow(CHIPS));
    }).catch(function () { log.appendChild(chipRow(CHIPS)); /* retried on the first question */ });

    form.addEventListener("submit", function (e) { e.preventDefault(); ask(input.value); });
    close.addEventListener("click", function () { show(false); });
    panel.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { show(false); return; }
      if (e.key !== "Tab") return;
      var items = panel.querySelectorAll("a[href],button,input,[tabindex='0']");
      var firstItem = items[0], lastItem = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstItem) { e.preventDefault(); lastItem.focus(); }
      else if (!e.shiftKey && document.activeElement === lastItem) { e.preventDefault(); firstItem.focus(); }
    });
    return { show: show };
  }
  return { create: create, makeIndex: makeIndex };
})();

/* Tax tools for vazassociates.in/tools/ — runs entirely in the browser; nothing is sent or stored.
   Rates as on 1 November 2026 (Income-tax Act, 2025; tax year 2026-27; CGST Act 2017 s.50). */
(function () {
  "use strict";
  var WA = "https://wa.me/919538416161?text=";
  var INF = Infinity;

  function $(id) { return document.getElementById(id); }
  function num(id) { var v = parseFloat(String($(id).value).replace(/[, ]/g, "")); return isFinite(v) && v > 0 ? v : 0; }
  function inr(n) { return "₹" + Math.round(n).toLocaleString("en-IN"); }
  function pct(n) { return (Math.round(n * 10000) / 100).toLocaleString("en-IN") + "%"; }
  function dateOf(id) { var v = $(id).value; if (!v) return null; var p = v.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function fmtDate(d) { return d.getDate() + " " + d.toLocaleString("en-GB", { month: "short" }) + " " + d.getFullYear(); }
  function track(name, tool) { if (window.gtag) gtag("event", name, { tool: tool }); }
  function row(label, value, strong) {
    return '<tr' + (strong ? ' class="t-total"' : "") + '><th scope="row">' + label + '</th><td class="num">' + value + "</td></tr>";
  }
  function show(outId, html, waText, tool) {
    var o = $(outId);
    o.innerHTML = html + '<p class="t-disclaimer">Estimate only, based on the figures entered and the law as on 1 November 2026. It is not advice; please obtain specific advice before acting.</p>' +
      '<p><a class="btn btn--primary t-wa" target="_blank" rel="noopener" href="' + WA + encodeURIComponent(waText) + '">Send these figures to Ryan on WhatsApp</a></p>';
    o.hidden = false;
    o.querySelector(".t-wa").addEventListener("click", function () { track("generate_lead", tool); });
    track("tool_calculate", tool);
  }

  /* ---------- Income-tax: slabs, rebate, surcharge, cess ---------- */
  var NEW_SLABS = [[400000, 0], [800000, .05], [1200000, .10], [1600000, .15], [2000000, .20], [2400000, .25], [INF, .30]];
  function oldSlabs(age) {
    var nil = age === "80" ? 500000 : age === "60" ? 300000 : 250000;
    var s = [[nil, 0]];
    if (nil < 500000) s.push([500000, .05]);
    s.push([1000000, .20], [INF, .30]);
    return s;
  }
  function slabTax(income, slabs) {
    var t = 0, prev = 0;
    for (var i = 0; i < slabs.length; i++) {
      var top = slabs[i][0];
      if (income > prev) t += (Math.min(income, top) - prev) * slabs[i][1];
      prev = top;
    }
    return t;
  }
  function baseTax(income, regime, age) {
    if (regime === "new") {
      var t = slabTax(income, NEW_SLABS);
      if (income <= 1200000) return 0;                       // rebate (s.156, formerly 87A)
      return Math.min(t, income - 1200000);                    // marginal relief on rebate
    }
    var o = slabTax(income, oldSlabs(age));
    if (income <= 500000) o = Math.max(0, o - 12500);
    return o;
  }
  function surRate(income, regime) {
    if (income > 50000000) return regime === "new" ? .25 : .37;
    if (income > 20000000) return .25;
    if (income > 10000000) return .15;
    if (income > 5000000) return .10;
    return 0;
  }
  function taxWithSurcharge(income, regime, age) {
    var t = baseTax(income, regime, age);
    var withSur = t * (1 + surRate(income, regime));
    // marginal relief on surcharge at each threshold
    var th = [5000000, 10000000, 20000000, 50000000];
    for (var i = 0; i < th.length; i++) {
      if (income > th[i]) {
        var atTh = baseTax(th[i], regime, age) * (1 + surRate(th[i], regime));
        withSur = Math.min(withSur, atTh + (income - th[i]));
      }
    }
    return { tax: t, surcharge: Math.max(0, withSur - t), total: withSur * 1.04, cess: withSur * .04 };
  }

  function calcRegime() {
    var age = $("r-age").value;
    var salary = num("r-salary"), other = num("r-other");
    var gross = salary + other;
    var npsEmp = num("r-nps-emp");
    var stdNew = salary > 0 ? Math.min(75000, salary) : 0;
    var stdOld = salary > 0 ? Math.min(50000, salary) : 0;
    var c80 = Math.min(num("r-80c"), 150000), d80 = num("r-80d"), hra = num("r-hra"), hl = Math.min(num("r-homeloan"), 200000), oth = num("r-otherded");
    var newInc = Math.max(0, gross - stdNew - npsEmp);
    var oldDed = stdOld + c80 + d80 + hra + hl + oth + npsEmp;
    var oldInc = Math.max(0, gross - oldDed);
    var n = taxWithSurcharge(newInc, "new", age), o = taxWithSurcharge(oldInc, "old", age);
    var better = n.total < o.total ? "new" : o.total < n.total ? "old" : "same";
    var diff = Math.abs(n.total - o.total);
    var html = '<h3 class="t-result-title">' + (better === "same" ? "Both regimes give the same tax." :
      "The " + better + " regime is lower by " + inr(diff) + ".") + "</h3>" +
      '<div class="table-wrap"><table class="t-table"><thead><tr><th scope="col"></th><th scope="col" class="num">New regime</th><th scope="col" class="num">Old regime</th></tr></thead><tbody>' +
      "<tr><th scope=\"row\">Gross income</th><td class=\"num\">" + inr(gross) + "</td><td class=\"num\">" + inr(gross) + "</td></tr>" +
      "<tr><th scope=\"row\">Deductions</th><td class=\"num\">" + inr(stdNew + npsEmp) + "</td><td class=\"num\">" + inr(Math.min(oldDed, gross)) + "</td></tr>" +
      "<tr><th scope=\"row\">Taxable income</th><td class=\"num\">" + inr(newInc) + "</td><td class=\"num\">" + inr(oldInc) + "</td></tr>" +
      "<tr><th scope=\"row\">Tax after rebate</th><td class=\"num\">" + inr(n.tax) + "</td><td class=\"num\">" + inr(o.tax) + "</td></tr>" +
      "<tr><th scope=\"row\">Surcharge</th><td class=\"num\">" + inr(n.surcharge) + "</td><td class=\"num\">" + inr(o.surcharge) + "</td></tr>" +
      "<tr><th scope=\"row\">Health and education cess (4%)</th><td class=\"num\">" + inr(n.cess) + "</td><td class=\"num\">" + inr(o.cess) + "</td></tr>" +
      "<tr class=\"t-total\"><th scope=\"row\">Total tax</th><td class=\"num\">" + inr(n.total) + "</td><td class=\"num\">" + inr(o.total) + "</td></tr>" +
      "</tbody></table></div>";
    var wa = "Hello Ryan, I used the regime calculator on your website. Gross income " + inr(gross) + ". New regime tax " + inr(n.total) + ", old regime tax " + inr(o.total) + ". I would like to discuss my return.";
    show("r-out", html, wa, "regime");
  }

  /* ---------- Advance tax ---------- */
  function calcAdvance() {
    var tax = num("a-tax"), presumptive = $("a-presumptive").checked;
    var paid = [num("a-p1"), num("a-p2"), num("a-p3"), num("a-p4")];
    var dates = ["15 June 2026", "15 September 2026", "15 December 2026", "15 March 2027"];
    var cum = presumptive ? [0, 0, 0, 1] : [.15, .45, .75, 1];
    var safe = presumptive ? [0, 0, 0, 1] : [.12, .36, .75, 1];
    var months = [3, 3, 3, 1];
    var html, wa;
    if (tax < 10000) {
      html = '<h3 class="t-result-title">No advance tax is payable.</h3><p>Advance tax applies only when the tax for the year, after TDS and TCS, is ' + inr(10000) + " or more. Pay any balance as self-assessment tax before filing the return.</p>";
      show("a-out", html, "Hello Ryan, I used the advance tax calculator on your website. My estimated tax after TDS is " + inr(tax) + ".", "advance-tax");
      return;
    }
    var rows = "", totalInt = 0, cumPaid = 0;
    for (var i = 0; i < 4; i++) {
      cumPaid += paid[i];
      var due = tax * cum[i];
      var interest = 0;
      if (cum[i] > 0 && cumPaid < tax * safe[i]) {
        var short = Math.floor(Math.max(0, due - cumPaid) / 100) * 100;
        interest = short * .01 * months[i];
      }
      totalInt += interest;
      rows += "<tr><td>" + dates[i] + '</td><td class="num">' + (cum[i] ? Math.round(cum[i] * 100) + "%" : "-") + '</td><td class="num">' + inr(due) + '</td><td class="num">' + inr(cumPaid) + '</td><td class="num">' + inr(interest) + "</td></tr>";
    }
    var shortfall90 = cumPaid < tax * .9;
    html = '<h3 class="t-result-title">' + (totalInt > 0 ? "Interest for deferment: " + inr(totalInt) : "No interest for deferment on these payments.") + "</h3>" +
      '<div class="table-wrap"><table class="t-table"><thead><tr><th scope="col">Due date</th><th scope="col" class="num">Cumulative %</th><th scope="col" class="num">Cumulative due</th><th scope="col" class="num">Paid so far</th><th scope="col" class="num">Interest</th></tr></thead><tbody>' +
      rows + "</tbody></table></div>" +
      (shortfall90 ? '<p class="t-warn">Advance tax paid is below 90% of the tax for the year. Further interest of 1% a month on the shortfall runs from 1 April 2027 until the tax is paid (formerly section 234B). This is not included above.</p>' : "");
    wa = "Hello Ryan, I used the advance tax calculator on your website. Estimated tax after TDS " + inr(tax) + ", advance tax paid " + inr(cumPaid) + ", interest estimate " + inr(totalInt) + ".";
    show("a-out", html, wa, "advance-tax");
  }

  /* ---------- TDS on property bought from an NRI ---------- */
  function calcNri() {
    var price = num("n-price"), term = $("n-term").value, cert = $("n-cert").checked, certRate = num("n-certrate") / 100, certAmt = num("n-certamt");
    var base, sur, rate;
    if (term === "lt") {
      base = .125;
      sur = price > 10000000 ? .15 : price > 5000000 ? .10 : 0;            // capped at 15% for long-term gains
    } else {
      base = .30;
      sur = price > 20000000 ? .25 : price > 10000000 ? .15 : price > 5000000 ? .10 : 0;
    }
    rate = base * (1 + sur) * 1.04;
    var tds = price * rate, html, note = "";
    if (cert && (certRate > 0 || certAmt > 0)) {
      var certTds = certAmt > 0 ? certAmt : price * certRate;
      note = row("TDS under your lower deduction certificate", inr(certTds), true);
      html = '<h3 class="t-result-title">TDS as per your certificate: ' + inr(certTds) + "</h3>";
    } else {
      html = '<h3 class="t-result-title">TDS to deduct: ' + inr(tds) + " (" + pct(rate) + " of the price)</h3>";
    }
    html += '<div class="table-wrap"><table class="t-table"><tbody>' +
      row("Sale price", inr(price)) +
      row(term === "lt" ? "Rate for long-term gain (held over 24 months)" : "Rate for short-term gain (held 24 months or less)", pct(base)) +
      row("Surcharge", pct(sur)) + row("Health and education cess", "4%") +
      row("Effective TDS rate", pct(rate)) +
      row("TDS on the full sale price", inr(tds), !note) + note +
      row("Net amount payable to the seller", inr(price - (note ? (certAmt > 0 ? certAmt : price * certRate) : tds))) +
      "</tbody></table></div>" +
      '<ul class="t-points"><li>Without a lower deduction certificate, TDS is on the full sale price, not only on the gain. The seller can apply on TRACES for a lower deduction certificate before the sale so that TDS is limited to the tax on the gain.</li>' +
      "<li>From 1 October 2026, a buyer who is a resident individual or HUF can deduct and deposit this TDS using a PAN-based challan-cum-statement, without a TAN. Companies and firms still need a TAN.</li>" +
      "<li>The buyer must issue a TDS certificate to the seller. If the seller has no PAN, a higher rate applies.</li></ul>";
    var wa = "Hello Ryan, I used the NRI property TDS calculator on your website. Sale price " + inr(price) + ", " + (term === "lt" ? "long-term" : "short-term") + ". TDS estimate " + inr(tds) + ". I would like help with the TDS and filings.";
    show("n-out", html, wa, "nri-tds");
  }

  /* ---------- Late payment interest ---------- */
  function monthsInclusive(a, b) { return (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth()) + 1; }
  function tdsDueDate(ded) {
    if (ded.getMonth() === 2) return new Date(ded.getFullYear(), 3, 30);   // March deductions: 30 April
    return new Date(ded.getFullYear(), ded.getMonth() + 1, 7);
  }
  function calcLate() {
    var type = $("l-type").value, amt = num("l-amount"), html, wa, total = 0;
    if (type === "tds") {
      var dueToDeduct = dateOf("l-ddate"), deducted = dateOf("l-dded"), paid = dateOf("l-paid");
      if (!dueToDeduct || !deducted || !paid) { $("l-out").innerHTML = '<p class="t-warn">Please enter all three dates.</p>'; $("l-out").hidden = false; return; }
      var m1 = deducted > dueToDeduct ? monthsInclusive(dueToDeduct, deducted) : 0;
      var due = tdsDueDate(deducted);
      var m2 = paid > due ? monthsInclusive(deducted, paid) : 0;
      var i1 = amt * .01 * m1, i2 = amt * .015 * m2; total = i1 + i2;
      html = '<h3 class="t-result-title">Interest payable: ' + inr(total) + "</h3>" +
        '<div class="table-wrap"><table class="t-table"><tbody>' +
        row("TDS amount", inr(amt)) +
        row("Late deduction: " + m1 + " month" + (m1 === 1 ? "" : "s") + " at 1%", inr(i1)) +
        row("Due date for deposit", fmtDate(due)) +
        row("Late deposit: " + m2 + " month" + (m2 === 1 ? "" : "s") + " at 1.5%", inr(i2)) +
        row("Total interest", inr(total), true) + "</tbody></table></div>" +
        '<p class="muted">Section 398(3)(a) of the Income-tax Act, 2025. A part of a month counts as a full month. Interest must be paid before the TDS statement is filed. A late filing fee and penalty can apply separately.</p>';
      wa = "Hello Ryan, I used the late payment interest calculator on your website. TDS " + inr(amt) + ", interest estimate " + inr(total) + ".";
    } else {
      var gdue = dateOf("l-gdue"), gpaid = dateOf("l-gpaid");
      if (!gdue || !gpaid) { $("l-out").innerHTML = '<p class="t-warn">Please enter both dates.</p>'; $("l-out").hidden = false; return; }
      var days = Math.max(0, Math.round((gpaid - gdue) / 86400000));
      total = amt * .18 * days / 365;
      html = '<h3 class="t-result-title">Interest payable: ' + inr(total) + "</h3>" +
        '<div class="table-wrap"><table class="t-table"><tbody>' +
        row("Tax paid late (cash portion)", inr(amt)) + row("Days late", days.toLocaleString("en-IN")) +
        row("Rate", "18% a year") + row("Interest", inr(total), true) + "</tbody></table></div>" +
        '<p class="muted">Section 50 of the CGST Act. Interest is on the part of the tax paid through the cash ledger. Input tax credit wrongly availed and utilised attracts interest at 24% a year, which is not covered here.</p>';
      wa = "Hello Ryan, I used the GST late payment interest calculator on your website. Tax " + inr(amt) + " paid " + days + " days late, interest estimate " + inr(total) + ".";
    }
    show("l-out", html, wa, "late-interest");
  }

  /* ---------- Tabs ---------- */
  function initTabs() {
    var tabs = [].slice.call(document.querySelectorAll('[role="tab"]'));
    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        $(t.getAttribute("aria-controls")).hidden = !on;
      });
      if (focus) tab.focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () {
        select(t);
        if (history.replaceState) history.replaceState(null, "", "#" + t.getAttribute("aria-controls"));
      });
      t.addEventListener("keydown", function (e) {
        var k = e.key, j = null;
        if (k === "ArrowRight") j = (i + 1) % tabs.length;
        if (k === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
        if (k === "Home") j = 0;
        if (k === "End") j = tabs.length - 1;
        if (j !== null) { e.preventDefault(); select(tabs[j], true); tabs[j].click(); }
      });
    });
    function fromHash() {
      var h = location.hash.replace("#", "");
      var t = tabs.filter(function (x) { return x.getAttribute("aria-controls") === h; })[0];
      select(t || tabs[0]);
      if (t) { var w = document.getElementById("tool-tabs"); if (w) w.scrollIntoView(); }
    }
    window.addEventListener("hashchange", fromHash);
    fromHash();
  }

  function init() {
    if (!$("tool-tabs")) return;
    initTabs();
    $("f-regime").addEventListener("submit", function (e) { e.preventDefault(); calcRegime(); });
    $("f-advance").addEventListener("submit", function (e) { e.preventDefault(); calcAdvance(); });
    $("f-nri").addEventListener("submit", function (e) { e.preventDefault(); calcNri(); });
    $("f-late").addEventListener("submit", function (e) { e.preventDefault(); calcLate(); });
    $("n-cert").addEventListener("change", function () { $("n-certbox").hidden = !this.checked; });
    $("l-type").addEventListener("change", function () {
      var g = this.value === "gst";
      $("l-tdsbox").hidden = g; $("l-gstbox").hidden = !g;
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();

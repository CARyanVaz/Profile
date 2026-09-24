/* Vaz & Associates — site behaviour (vanilla JS, no dependencies) */
(function () {
  "use strict";
  var root = document.documentElement;

  /* When pages are opened straight from disk (file://), folder links need an explicit index.html. */
  if (location.protocol === "file:") {
    document.querySelectorAll("a[href]").forEach(function (a) {
      var h = a.getAttribute("href");
      if (/^(https?:|mailto:|tel:|#)/.test(h)) return;
      var parts = h.split("#");
      if (parts[0] === "" || parts[0] === "./" ) parts[0] = "./";
      if (/\/$/.test(parts[0])) {
        parts[0] += "index.html";
        a.setAttribute("href", parts.join("#"));
      }
    });
  }

  /* Theme toggle: explicit choice is remembered; otherwise follows the OS setting. */
  var toggle = document.querySelector(".theme-toggle");
  function currentTheme() {
    var t = root.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function syncToggle() {
    if (!toggle) return;
    var dark = currentTheme() === "dark";
    toggle.setAttribute("aria-pressed", String(dark));
    toggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("va-theme", next); } catch (e) { /* storage unavailable */ }
      syncToggle();
    });
    syncToggle();
  }

  /* Mobile navigation */
  var navBtn = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (navBtn && nav) {
    navBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      navBtn.setAttribute("aria-expanded", String(open));
      navBtn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        navBtn.setAttribute("aria-expanded", "false");
        navBtn.focus();
      }
    });
  }

  /* Reveal on scroll (disabled automatically by CSS under prefers-reduced-motion) */
  var items = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* 3D pointer tilt on cards (desktop mouse only; off under reduced motion) */
  var fine = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (fine && !still) {
    document.querySelectorAll(".card, .firm-card, .stat, .portrait-photo img").forEach(function (el) {
      var max = el.classList.contains("firm-card") ? 6 : el.classList.contains("stat") ? 5 : 7;
      el.classList.add("tilt");
      var frame = 0;
      el.addEventListener("pointermove", function (e) {
        if (frame) return;
        frame = requestAnimationFrame(function () {
          frame = 0;
          var r = el.getBoundingClientRect();
          var px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
          el.classList.add("is-tilting");
          el.style.setProperty("--ry", ((px - 0.5) * 2 * max).toFixed(2) + "deg");
          el.style.setProperty("--rx", ((0.5 - py) * 2 * max).toFixed(2) + "deg");
          el.style.setProperty("--gx", (px * 100).toFixed(1) + "%");
          el.style.setProperty("--gy", (py * 100).toFixed(1) + "%");
        });
      });
      el.addEventListener("pointerleave", function () {
        el.classList.remove("is-tilting");
        el.style.setProperty("--rx", "0deg");
        el.style.setProperty("--ry", "0deg");
      });
    });
  }

  /* Footer year */
  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());

  /* Contact form.
     If data-endpoint is set to a form service URL (e.g. Formspree), the form is POSTed there.
     Otherwise it opens the visitor's email app with the message pre-filled. */
  var form = document.getElementById("contact-form");
  if (form) {
    var status = form.querySelector(".form-status");
    function say(msg, state) {
      status.textContent = msg;
      status.setAttribute("data-state", state || "ok");
    }
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (form.querySelector(".hp input").value) return; // spam trap
      if (!form.checkValidity()) {
        form.reportValidity();
        say("Please complete the required fields.", "error");
        return;
      }
      var data = new FormData(form);
      var endpoint = (form.getAttribute("data-endpoint") || "").trim();
      var to = (form.getAttribute("data-email") || "").trim();

      if (endpoint && endpoint.indexOf("[") !== 0) {
        say("Sending…");
        fetch(endpoint, { method: "POST", body: data, headers: { Accept: "application/json" } })
          .then(function (r) {
            if (!r.ok) throw new Error("Request failed");
            form.reset();
            say("Thank you. Your message has been sent.");
          })
          .catch(function () {
            say("The message could not be sent. Please call or email instead.", "error");
          });
        return;
      }

      var subject = "Enquiry: " + (data.get("topic") || "General");
      var body =
        "Name: " + data.get("name") + "\n" +
        "Email: " + data.get("email") + "\n" +
        "Phone: " + (data.get("phone") || "-") + "\n" +
        "Topic: " + (data.get("topic") || "-") + "\n\n" +
        data.get("message");
      window.location.href = "mailto:" + encodeURIComponent(to).replace("%40", "@") +
        "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
      say("Your email app should open with the message ready to send.");
    });
  }
})();

# caryanvaz.github.io — Vaz & Associates, Chartered Accountants

Static site (HTML, CSS, vanilla JS). No build step.

## Deploy to GitHub Pages
1. Copy everything in this folder (including the hidden `.nojekyll`) to the root of the `caryanvaz.github.io` repository.
2. Commit and push to the default branch. Pages serves it at https://caryanvaz.github.io/.
3. Submit `https://caryanvaz.github.io/sitemap.xml` in Google Search Console and Bing Webmaster Tools.

## Preview locally
    python3 -m http.server 8080
then open http://localhost:8080/ (paths are root-relative, so open via a server, not by double-clicking files).

## Contact form
Left as is, the form opens the visitor's email app addressed to ryan@vazassociates.in.
Optional: set `data-endpoint` on the form in contact/index.html to a form service URL (e.g. Formspree) to send directly.

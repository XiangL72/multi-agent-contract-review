# Static demo walkthrough

This buildless website presents a selected, recorded fictional trial. It does not run contract analysis, accept uploads, connect to a backend, or call a model. The recorded results predate the latest offline consistency checks; that distinction is visible on the page. Original Chinese source-summary quotations are preserved.

From the repository root, preview locally:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8765. Stop the server with Ctrl-C. Only the contents of `site/` are served. No frontend dependency install or build is needed.

Deployable page assets are `index.html`, `styles.css` and `demo.js`. The page uses local system fonts, no third-party assets, no analytics and no browser storage. A content security policy blocks connections and form submissions; text excerpts are rendered using `textContent`.

Publication is a separate step. No repository or hosted-demo link is shown until a real destination has been approved and verified. Review license/attribution obligations and the full publication candidate before publishing.

The local browser check covered the narrow viewport layout, click and keyboard stage navigation, and original source quotation display. Desktop and additional browser coverage remain pending; this is not an accessibility certification. The static preview does not establish current live-model quality.

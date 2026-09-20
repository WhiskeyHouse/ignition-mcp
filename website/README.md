# ignition-mcp documentation site

Install Node.js 22, then run these commands from `website/`:

```sh
npm ci
npm run build
npm run typecheck
npm start
```

The site uses Docusaurus. Edit user guides in `docs/`, navigation in `website/sidebars.ts`, and the landing page in `website/src/pages/index.tsx`. Internal design records remain in the repository and are excluded from the published site.

`website/sync-reference.py` runs before `build` and `start` and regenerates `docs/configuration.md` and `docs/reference.md` from the server source and the catalog snapshot in `docs/_generated/ign-catalog.json`; do not edit those two pages by hand. It uses only the Python standard library, because the docs CI job installs no Python dependencies. To refresh the catalog snapshot, a maintainer runs `uv run python website/snapshot-ign-catalog.py` with `ign` on `PATH`; that script is never run in CI.

Pull requests build the docs and check internal links. Main commits deploy to https://whiskeyhouse.github.io/ignition-mcp/ through GitHub Pages. Set the repository's Pages build source to GitHub Actions before its first deployment.

# Aviate Travel — GitHub Pages edition

This version runs entirely in visitors' browsers. The original Python search
engine runs with Pyodide in a background Web Worker. There is no Python server,
API key, build step, or paid hosting dependency. The first search downloads the
Python browser runtime; subsequent searches reuse it.

## Publish

1. Create a GitHub repository and upload the CONTENTS of this folder to its root,
   including the SB-*.txt data files. Do not upload just the ZIP file.
2. In repository Settings > Pages, choose Deploy from a branch, main, /(root), Save.
3. Wait for the Pages deployment to complete and open the displayed website URL.

Relative URLs support both username.github.io and username.github.io/repository/.
For local preview: python -m http.server 8090, then open http://localhost:8090/.
Opening index.html directly as a file does not support the worker and data fetches.

## Internet resources

Pyodide 0.28.3 loads from cdn.jsdelivr.net; Leaflet loads from unpkg.com;
globe.gl and country outlines load from cdn.jsdelivr.net; map tiles load from
tile.openstreetmap.org. Keep map attribution and ASSET-SOURCES.txt.
The bundled historical assignment datasets do not represent live flight availability.
The public copy omits the numeric student identifier and school email.


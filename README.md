# y-offline-pages

Static GitHub Pages for [Y-Offline](https://codeberg.org/cocvu/Y-Offline) rhythm game scores. Displays best-pool records with song jackets.

## Supported Games

- **Arcaea** — B50 + Top10 (v7.0 potential, experimental page `arcaea_v7.html`)
- **Project SEKAI** — B30
- **Cytus II** — B30

## Setup

1. Fork this repo
2. Copy `config.toml.example` to `config.toml` and fill in your paths
3. Install dependencies:
   ```bash
   pip install jinja2
   pip install -e /path/to/Y-Offline  # or pip install y-offline
   ```
4. Generate data and build:
   ```bash
   python generate.py
   python build.py
   ```
5. Preview locally: open `dist/index.html`
6. Push `data/` to trigger GitHub Actions deployment:
   ```bash
   git add data/
   git commit -m "update scores"
   git push
   ```
7. Enable GitHub Pages in repo settings (source: GitHub Actions)

## Config

```toml
[y_offline]
db_path = "/path/to/y_offline.db"

[arcaea]
arcsong_db_path = "/path/to/arcsong.db"

[pjsk]
musics_json_path = "/path/to/musics.json"
music_difficulties_json_path = "/path/to/musicDifficulties.json"

[cytus2]
charts_json_path = "/path/to/cytus2/charts.json"

[pages]
user = "your_user_id"
pjsk_jacket_cdn = "https://storage.sekai.best/sekai-jp-assets"
```

Game sections are optional — only configured games will be generated.

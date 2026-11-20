# The World in One Day — Friday 20 November 2026

[![news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/beecoder77/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/beecoder77/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120)

Entry for the [make.fun](https://make.fun/bounty/news-image-20261120)
competition `news-image-20261120`: sum up Friday 20 November 2026's world
news in one image.

## The image

A 1024×1024 newspaper front page with **42 verified stories across 7
regions**, drawn entirely in code:

- **Lead:** Cyclone Akvan makes landfall on India's east coast (Odisha,
  noon IST) — 300,000 evacuated, 423 rescue teams deployed.
- **Second leads:** Trump defers any Iran decision to 2027; the ICJ finds
  Myanmar guilty of genocide against the Rohingya (9–6, a first for a state).
- **Regions:** North America, Latin America, Europe, Middle East, Africa,
  Asia-Pacific, plus Science & Tech and Sport — with a UTC wire strip and a
  numbered world-map strip marking the 8 biggest stories.
- Every story was verified against a named source (IMD, Reuters, BBC, CNN,
  NASA, AP and others); estimates are labelled as estimates and nothing is
  invented.

## How it is made

`main.py` (Python 3.13, standard library only) draws the whole front page:
its own 5×7 bitmap font, its own vector drawing (cyclone spiral, coastline,
world map), and its own PNG encoder (`zlib`/`struct`). No network, no
randomness, no timestamps — two runs write byte-identical output.

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png (1024x1024, ~36 KB)
```

## Licence

MIT — see [LICENSE](LICENSE).

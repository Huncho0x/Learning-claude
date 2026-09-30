# Rinse & Repeat — jeans on a rail

A small shop page where jeans hang side-on on a chrome rail. Hover a pair and it turns round to face you, swinging on its hanger like real fabric; click it to pick a waist size and add it to your bag. The page is just the rail: no header, logo or banner.

The pictures in `public/garments` are made from one real product photo (`scripts/source/jeans-photo.png`) by `scripts/build_garments.py`: it cuts the photo out, reshapes the legs for each fit, re-dyes it for each wash, hangs it on a clip hanger and makes a side view for the rail.

## Run it on your Mac

Open Terminal and run these one at a time:

```bash
cd Learning-claude/jeans-rack
npm install
npm run dev
```

Then open http://localhost:3000 in your browser. Press `Ctrl + C` in Terminal to stop it.

## Change things

- **Pairs, prices, sizes and stock:** `app/data.js`. Each pair is one block.
- **Shop name, email and currency:** the `BRAND` block at the top of `app/data.js`.
- **Colours and layout:** `app/globals.css`.
- **Pictures:** after changing a pair's `fit` or `wash`, or swapping the source photo, run `python3 -m pip install numpy pillow scipy` once, then `python3 scripts/build_garments.py`.

## Put it online with Vercel

1. Go to https://vercel.com/new and pick the `Learning-claude` repository.
2. Set **Root Directory** to `jeans-rack`.
3. Click **Deploy**. Vercel gives you a link when it finishes, and redeploys every time you push.

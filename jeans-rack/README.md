# Rinse & Repeat — jeans on a rail

A small shop page where jeans and trousers hang on a chrome rail. Hover a pair and it swings round to face you; click it to pick a waist size and add it to your bag. "See availability" shows every size at a glance.

The jeans are drawn in code as placeholders, so there are no image files yet.

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
- **Real photos:** drop a picture (ideally a cut-out PNG with a see-through background) into a `public` folder here, then add `image: "/your-photo.png"` to that pair in `app/data.js`.

## Put it online with Vercel

1. Go to https://vercel.com/new and pick the `Learning-claude` repository.
2. Set **Root Directory** to `jeans-rack`.
3. Click **Deploy**. Vercel gives you a link when it finishes, and redeploys every time you push.

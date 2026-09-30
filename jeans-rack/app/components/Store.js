"use client";

import { useEffect, useRef, useState } from "react";
import { BRAND, PRODUCTS, SIZES, totalStock } from "../data";

const RAIL_WIDTH = 900;
const RAIL_HEIGHT = 470;
const SLOT_REST = 62; // width of a pair hanging side-on
const SLOT_OPEN = 250; // width once it has turned to face you

const front = (p) => `/garments/${p.id}-front.webp`;
const side = (p) => `/garments/${p.id}-side.webp`;

export default function Store() {
  const [active, setActive] = useState(null); // pair swung to face you
  const [viewing, setViewing] = useState(null); // pair opened in the detail panel
  const [bagOpen, setBagOpen] = useState(false);
  const [bag, setBag] = useState([]);

  function addToBag(product, size) {
    setBag((items) => {
      const found = items.find((i) => i.id === product.id && i.size === size);
      if (found) {
        return items.map((i) => (i === found ? { ...i, qty: i.qty + 1 } : i));
      }
      return [...items, { id: product.id, size, qty: 1 }];
    });
    setViewing(null);
    setBagOpen(true);
  }

  function removeFromBag(index) {
    setBag((items) => items.filter((_, i) => i !== index));
  }

  return (
    <div className="site">
      <main className="stage">
        <Rail active={active} setActive={setActive} onOpen={setViewing} />
      </main>

      {viewing && (
        <Modal onClose={() => setViewing(null)} wide>
          <ProductDetail product={viewing} onAdd={addToBag} />
        </Modal>
      )}

      {bagOpen && (
        <Modal onClose={() => setBagOpen(false)} title="Your bag">
          <Bag items={bag} onRemove={removeFromBag} />
        </Modal>
      )}
    </div>
  );
}

function Rail({ active, setActive, onOpen }) {
  const wrapRef = useRef(null);
  const tap = useRef({ touch: false, wasActive: false });
  const [scale, setScale] = useState(1);
  const { itemRefs, push } = useClothPhysics(active);

  // Shrink the rail to fit the screen. On phones it stops shrinking at a readable
  // size and you swipe sideways along the rail instead.
  useEffect(() => {
    function fit() {
      const wrap = wrapRef.current;
      if (!wrap) return;
      const s = Math.max(0.6, Math.min(1, wrap.clientWidth / RAIL_WIDTH));
      setScale(s);
      wrap.scrollLeft = (RAIL_WIDTH * s - wrap.clientWidth) / 2;
    }
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  // Brushing the pointer across the rail knocks the pairs it passes, like running a hand along it.
  const lastX = useRef(null);
  function brush(e, i) {
    if (e.pointerType !== "mouse") return;
    const dx = lastX.current === null ? 0 : e.clientX - lastX.current;
    lastX.current = e.clientX;
    push(i, Math.max(-30, Math.min(30, dx * 1.2)));
  }

  return (
    <div className="rail-wrap" ref={wrapRef}>
      <div className="rail-sizer" style={{ width: RAIL_WIDTH * scale, height: RAIL_HEIGHT * scale }}>
        <div className="rail-scaler" style={{ transform: `scale(${scale})`, "--scale": scale }}>
          <div className="rail-bar">
            <span className="bracket left" />
            <span className="pole" />
            <span className="bracket right" />
          </div>
          <ul
            className="rack"
            onPointerLeave={(e) => {
              lastX.current = null;
              if (e.pointerType === "mouse") setActive(null);
            }}
          >
            {PRODUCTS.map((p, i) => {
              const isActive = active === p.id;
              const soldOut = totalStock(p) === 0;
              return (
                <li
                  key={p.id}
                  ref={(el) => (itemRefs.current[i] = el)}
                  className={`slot${isActive ? " is-active" : ""}`}
                  onPointerEnter={(e) => e.pointerType === "mouse" && setActive(p.id)}
                  onPointerMove={(e) => brush(e, i)}
                >
                  <button
                    className="garment"
                    aria-label={`${p.name}, ${p.colour}, ${BRAND.currency}${p.price}${soldOut ? ", sold out" : ""}`}
                    onFocus={() => setActive(p.id)}
                    onPointerDown={(e) => {
                      tap.current = { touch: e.pointerType !== "mouse", wasActive: isActive };
                    }}
                    onClick={() => {
                      // On touch screens the first tap turns it round, the second opens it.
                      const { touch, wasActive } = tap.current;
                      tap.current = { touch: false, wasActive: false };
                      if (touch && !wasActive) {
                        setActive(p.id);
                      } else {
                        onOpen(p);
                      }
                    }}
                  >
                    <span className="hang">
                      <span className="cloth">
                        <img className="face side" src={side(p)} alt="" draggable="false" />
                        <img className="face front" src={front(p)} alt="" draggable="false" />
                      </span>
                    </span>
                  </button>
                  <span className="label" aria-hidden={!isActive}>
                    {p.name} — {p.colour}
                    <em>
                      {BRAND.currency}
                      {p.price}
                    </em>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}

// A tiny spring simulation for every pair on the rail:
//   turn  swings it from side-on (0) to facing you (1), overshooting a little like a real hanger
//   swing is the whole pair rocking on its hook, slowly losing energy
//   lag   is the hem trailing behind the waistband, which is what makes it read as fabric
function useClothPhysics(active) {
  const itemRefs = useRef([]);
  const state = useRef(PRODUCTS.map(() => ({ t: 0, vt: 0, a: 0, va: 0, l: 0, vl: 0 })));
  const frame = useRef(null);
  const prevActive = useRef(null);
  const calm = useRef(false);

  function paint() {
    state.current.forEach((s, i) => {
      const el = itemRefs.current[i];
      if (!el) return;
      const t = Math.max(0, s.t);
      el.style.width = `${SLOT_REST + (SLOT_OPEN - SLOT_REST) * Math.min(1, t)}px`;
      el.style.setProperty("--swing", `${s.a.toFixed(3)}deg`);
      el.style.setProperty("--lag", `${((s.l - s.a) * 0.7).toFixed(3)}deg`);
      el.style.setProperty("--front-turn", `${((1 - s.t) * 88).toFixed(2)}deg`);
      el.style.setProperty("--side-turn", `${(-s.t * 88).toFixed(2)}deg`);
      el.style.setProperty("--front-show", smooth(0.12, 0.45, s.t).toFixed(3));
      el.style.setProperty("--side-show", (1 - smooth(0.3, 0.6, s.t)).toFixed(3));
    });
  }

  function step(dt) {
    const target = PRODUCTS.map((p) => (p.id === prevActive.current ? 1 : 0));
    let moving = false;
    state.current.forEach((s, i) => {
      // turn: stiff, a little bouncy
      s.vt += (140 * (target[i] - s.t) - 13 * s.vt) * dt;
      s.t += s.vt * dt;
      // swing: soft pendulum, light damping so it rocks a few times
      s.va += (-38 * s.a - 1.9 * s.va) * dt;
      s.a += s.va * dt;
      // hem follows the swing a beat late
      s.vl += (70 * (s.a - s.l) - 7 * s.vl) * dt;
      s.l += s.vl * dt;
      if (Math.abs(s.vt) + Math.abs(target[i] - s.t) + Math.abs(s.va) + Math.abs(s.a) + Math.abs(s.vl) > 0.004) moving = true;
      else {
        s.t = target[i];
        s.a = s.va = s.l = s.vl = s.vt = 0;
      }
    });
    return moving;
  }

  function run() {
    if (frame.current) return;
    let last = performance.now();
    const tick = (now) => {
      const dt = Math.min(0.032, (now - last) / 1000);
      last = now;
      // two half steps keep the springs stable on slow frames
      const moving = step(dt / 2) | step(dt / 2);
      paint();
      frame.current = moving ? requestAnimationFrame(tick) : null;
    };
    frame.current = requestAnimationFrame(tick);
  }

  function push(i, amount) {
    if (calm.current || !amount) return;
    const s = state.current[i];
    if (s) s.va += amount;
    run();
  }

  // When a new pair is picked it turns out, swings, and knocks its neighbours.
  useEffect(() => {
    const from = PRODUCTS.findIndex((p) => p.id === prevActive.current);
    const to = PRODUCTS.findIndex((p) => p.id === active);
    prevActive.current = active;
    if (to >= 0 && !calm.current) {
      const dir = from >= 0 && from > to ? -1 : 1;
      state.current[to].va += 42 * dir;
      if (state.current[to - 1]) state.current[to - 1].va -= 16;
      if (state.current[to + 1]) state.current[to + 1].va += 16;
    }
    run();
  }, [active]);

  // A draught every so often so the rail never looks frozen.
  useEffect(() => {
    calm.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    paint();
    if (calm.current) return;
    const id = setInterval(() => {
      const i = Math.floor(Math.random() * PRODUCTS.length);
      push(i, (Math.random() - 0.5) * 16);
    }, 2200);
    return () => {
      clearInterval(id);
      cancelAnimationFrame(frame.current);
      frame.current = null;
    };
  }, []);

  return { itemRefs, push, run };
}

function smooth(a, b, x) {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

function ProductDetail({ product, onAdd }) {
  const [size, setSize] = useState(null);
  const left = size ? product.stock[size] : null;

  return (
    <div className="detail">
      <div className="detail-art">
        <img src={front(product)} alt={`${product.name}, ${product.colour}`} className="detail-img" />
      </div>
      <div className="detail-info">
        <p className="eyebrow">Denim</p>
        <h2>{product.name}</h2>
        <p className="muted">{product.colour}</p>
        <p className="price">{BRAND.currency}{product.price}</p>
        <p>{product.description}</p>

        <p className="eyebrow">Waist size</p>
        <div className="sizes">
          {SIZES.map((s) => {
            const n = product.stock[s];
            return (
              <button
                key={s}
                className={`size${size === s ? " is-picked" : ""}`}
                disabled={n === 0}
                onClick={() => setSize(s)}
                title={n === 0 ? "Sold out" : `${n} left`}
              >
                {s}
              </button>
            );
          })}
        </div>
        <p className="stock-note">
          {left === null ? "Pick a size to see stock." : left <= 2 ? `Only ${left} left in ${size}.` : `${left} in stock.`}
        </p>

        <button className="pill solid" disabled={!size} onClick={() => onAdd(product, size)}>
          Add to bag
        </button>
      </div>
    </div>
  );
}

function Bag({ items, onRemove }) {
  const [checkedOut, setCheckedOut] = useState(false);
  if (items.length === 0) return <p className="muted">Nothing in here yet. Pick a pair off the rail.</p>;

  const lines = items.map((item) => ({ ...item, product: PRODUCTS.find((p) => p.id === item.id) }));
  const total = lines.reduce((sum, l) => sum + l.product.price * l.qty, 0);

  return (
    <div className="bag">
      <ul>
        {lines.map((l, i) => (
          <li key={`${l.id}-${l.size}`}>
            <span className="swatch" style={{ background: l.product.wash }} />
            <span className="bag-name">
              {l.product.name} — {l.product.colour}
              <span className="muted"> · W{l.size} · ×{l.qty}</span>
            </span>
            <span>{BRAND.currency}{l.product.price * l.qty}</span>
            <button className="text-btn" onClick={() => onRemove(i)}>Remove</button>
          </li>
        ))}
      </ul>
      <p className="bag-total">
        <span>Total</span>
        <strong>{BRAND.currency}{total}</strong>
      </p>
      {checkedOut ? (
        <p className="muted">Checkout isn&apos;t connected yet. This is a demo shop.</p>
      ) : (
        <button className="pill solid" onClick={() => setCheckedOut(true)}>Checkout</button>
      )}
    </div>
  );
}

function Modal({ title, onClose, wide, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className={`modal${wide ? " wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="close" onClick={onClose} aria-label="Close">×</button>
        {title && <h2 className="modal-title">{title}</h2>}
        {children}
      </div>
    </div>
  );
}

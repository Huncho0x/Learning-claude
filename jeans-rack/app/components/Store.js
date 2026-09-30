"use client";

import { useEffect, useRef, useState } from "react";
import Jeans from "./Jeans";
import { BRAND, PRODUCTS, SIZES, totalStock } from "../data";

// Each pair hangs at a slightly different angle so the rail looks lived-in.
const RAIL_WIDTH = 900;
const RAIL_HEIGHT = 470;
const RESTING_TURN = [74, 70, 78, 72, 76, 71, 75, 73, 77];

export default function Store() {
  const [active, setActive] = useState(null); // pair swung to face you
  const [viewing, setViewing] = useState(null); // pair opened in the detail panel
  const [panel, setPanel] = useState(null); // "about" | "contact" | "availability" | "bag"
  const [bag, setBag] = useState([]);

  const bagCount = bag.reduce((n, item) => n + item.qty, 0);

  function addToBag(product, size) {
    setBag((items) => {
      const found = items.find((i) => i.id === product.id && i.size === size);
      if (found) {
        return items.map((i) => (i === found ? { ...i, qty: i.qty + 1 } : i));
      }
      return [...items, { id: product.id, size, qty: 1 }];
    });
    setViewing(null);
    setPanel("bag");
  }

  function removeFromBag(index) {
    setBag((items) => items.filter((_, i) => i !== index));
  }

  return (
    <div className="site">
      <header className="top">
        <button className="navlink" onClick={() => setPanel("about")}>About</button>
        <a className="logo" href="/" aria-label={`${BRAND.line1} ${BRAND.line2}, home`}>
          <span>{BRAND.line1}</span>
          <span className="logo-2">{BRAND.line2}</span>
        </a>
        <div className="nav-right">
          <button className="navlink" onClick={() => setPanel("contact")}>Contact</button>
          <button className="navlink bag-link" onClick={() => setPanel("bag")}>
            Bag{bagCount > 0 && <span className="bag-count">{bagCount}</span>}
          </button>
        </div>
      </header>

      <main className="stage">
        <Rail active={active} setActive={setActive} onOpen={setViewing} />
        <button className="pill" onClick={() => setPanel("availability")}>See availability</button>
      </main>

      <Ticker onClick={() => setPanel("contact")} />

      {viewing && (
        <Modal onClose={() => setViewing(null)} wide>
          <ProductDetail product={viewing} onAdd={addToBag} />
        </Modal>
      )}

      {panel === "about" && (
        <Modal onClose={() => setPanel(null)} title="About">
          <p>
            {BRAND.line1} {BRAND.line2} is a small denim shop. We buy a few good pairs at a time,
            hang them on one rail, and restock when they are gone.
          </p>
          <p>Hover over a pair to swing it round. Click it to pick a size.</p>
        </Modal>
      )}

      {panel === "contact" && (
        <Modal onClose={() => setPanel(null)} title="Contact">
          <p>
            Questions about sizing, orders or restocks? Email us at{" "}
            <a href={`mailto:${BRAND.email}`}>{BRAND.email}</a>.
          </p>
          <Newsletter />
        </Modal>
      )}

      {panel === "availability" && (
        <Modal onClose={() => setPanel(null)} title="Availability" wide>
          <Availability
            onPick={(p) => {
              setPanel(null);
              setViewing(p);
            }}
          />
        </Modal>
      )}

      {panel === "bag" && (
        <Modal onClose={() => setPanel(null)} title="Your bag">
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

  return (
    <div className="rail-wrap" ref={wrapRef}>
      <div className="rail-sizer" style={{ width: RAIL_WIDTH * scale, height: RAIL_HEIGHT * scale }}>
      <div className="rail-scaler" style={{ transform: `scale(${scale})`, "--scale": scale }}>
        <div className="rail-bar">
          <span className="bracket left" />
          <span className="pole" />
          <span className="bracket right" />
        </div>
        <ul className="rack" onPointerLeave={(e) => e.pointerType === "mouse" && setActive(null)}>
          {PRODUCTS.map((p, i) => {
            const isActive = active === p.id;
            const soldOut = totalStock(p) === 0;
            return (
              <li
                key={p.id}
                className={`slot${isActive ? " is-active" : ""}`}
                style={{ "--turn": `${RESTING_TURN[i % RESTING_TURN.length]}deg` }}
                onPointerEnter={(e) => e.pointerType === "mouse" && setActive(p.id)}
              >
                <button
                  className="garment"
                  aria-label={`${p.name}, ${p.colour}, ${BRAND.currency}${p.price}${soldOut ? ", sold out" : ""}`}
                  onFocus={() => setActive(p.id)}
                  onPointerDown={(e) => {
                    tap.current = { touch: e.pointerType !== "mouse", wasActive: isActive };
                  }}
                  onClick={() => {
                    // On touch screens the first tap swings it round, the second opens it.
                    const { touch, wasActive } = tap.current;
                    tap.current = { touch: false, wasActive: false };
                    if (touch && !wasActive) {
                      setActive(p.id);
                    } else {
                      onOpen(p);
                    }
                  }}
                >
                  <span className="swing">
                    <span className="turn">
                      <Jeans product={p} className="garment-svg" />
                    </span>
                  </span>
                </button>
                <span className="label" aria-hidden={!isActive}>
                  {p.name} — {p.colour}
                  <em>{BRAND.currency}{p.price}</em>
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

function ProductDetail({ product, onAdd }) {
  const [size, setSize] = useState(null);
  const left = size ? product.stock[size] : null;

  return (
    <div className="detail">
      <div className="detail-art">
        <Jeans product={product} className="detail-svg" />
      </div>
      <div className="detail-info">
        <p className="eyebrow">{product.kind === "jeans" ? "Denim" : "Trousers"}</p>
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

function Availability({ onPick }) {
  return (
    <div className="table-scroll">
      <table className="avail">
        <thead>
          <tr>
            <th>Pair</th>
            {SIZES.map((s) => (
              <th key={s}>{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PRODUCTS.map((p) => (
            <tr key={p.id} onClick={() => onPick(p)}>
              <td>
                <span className="swatch" style={{ background: p.wash }} />
                {p.name} <span className="muted">— {p.colour}</span>
              </td>
              {SIZES.map((s) => {
                const n = p.stock[s];
                const state = n === 0 ? "out" : n <= 2 ? "low" : "in";
                return (
                  <td key={s}>
                    <span className={`dot ${state}`} title={n === 0 ? "Sold out" : `${n} left`} />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="legend">
        <span className="dot in" /> In stock <span className="dot low" /> Last few <span className="dot out" /> Sold out
      </p>
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

function Newsletter() {
  const [done, setDone] = useState(false);
  if (done) return <p className="muted">You&apos;re on the list. New washes land in your inbox first.</p>;
  return (
    <form
      className="newsletter"
      onSubmit={(e) => {
        e.preventDefault();
        setDone(true);
      }}
    >
      <label htmlFor="email">Newsletter</label>
      <div>
        <input id="email" type="email" required placeholder="you@example.com" />
        <button className="pill solid" type="submit">Subscribe</button>
      </div>
    </form>
  );
}

function Ticker({ onClick }) {
  const phrases = ["New washes weekly", "Subscribe to our newsletter", "Free hemming on every pair"];
  const row = Array.from({ length: 4 }, () => phrases).flat();
  return (
    <button className="ticker" onClick={onClick} aria-label="Subscribe to our newsletter">
      <span className="ticker-track">
        {[0, 1].map((copy) => (
          <span className="ticker-copy" key={copy} aria-hidden={copy === 1}>
            {row.map((t, i) => (
              <span key={i}>
                {t}
                <b>•</b>
              </span>
            ))}
          </span>
        ))}
      </span>
    </button>
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

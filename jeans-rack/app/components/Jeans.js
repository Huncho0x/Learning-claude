// A drawn pair of jeans (or trousers) on a clip hanger.
// These are placeholders: swap in real photos later by giving a product an `image`.

const HEM_Y = 372;
const CROTCH = { x: 100, y: 150 };

// Left-leg outline for each fit. The right leg is a mirror image.
// ox = outer edge at the hem, w = hem width, c1/c2 = curve of the outer seam.
const FITS = {
  straight: { ox: 36, w: 54, c1: [40, 150], c2: [36, 260] },
  wide: { ox: 16, w: 78, c1: [38, 150], c2: [18, 260] },
  slim: { ox: 52, w: 38, c1: [38, 140], c2: [50, 250] },
  baggy: { ox: 22, w: 72, c1: [26, 160], c2: [20, 280] },
  carpenter: { ox: 30, w: 62, c1: [34, 150], c2: [30, 270] },
  flare: { ox: 18, w: 76, c1: [42, 170], c2: [56, 270] },
  cargo: { ox: 28, w: 62, c1: [30, 160], c2: [26, 280] },
  pleated: { ox: 32, w: 58, c1: [36, 150], c2: [32, 270] },
  barrel: { ox: 46, w: 46, c1: [18, 190], c2: [26, 310] },
};

function legPath(fit) {
  const { ox, w, c1, c2 } = FITS[fit] || FITS.straight;
  const ix = ox + w;
  return [
    `M${CROTCH.x},44 L42,44 L42,64`,
    `C${c1[0]},${c1[1]} ${c2[0]},${c2[1]} ${ox},${HEM_Y}`,
    `L${ix},${HEM_Y + 2}`,
    `C${ix + 2},290 ${CROTCH.x - 3},200 ${CROTCH.x},${CROTCH.y} Z`,
  ].join(" ");
}

function legCentre(fit) {
  const { ox, w } = FITS[fit] || FITS.straight;
  return ox + w / 2;
}

export default function Jeans({ product, className, title }) {
  const { id, fit, wash, stitch, kind } = product;
  const label = title || `${product.name}, ${product.colour}`;

  // A real photo wins over the drawing. A cut-out PNG on a transparent background looks best.
  if (product.image) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={product.image} alt={label} className={className} draggable="false" />;
  }

  const isJeans = kind === "jeans";
  const p = `j-${id}`; // unique prefix so gradients don't clash between pairs
  const leg = legPath(fit);
  const hemMid = legCentre(fit);
  const stitchProps = {
    fill: "none",
    stroke: stitch,
    strokeWidth: 1.1,
    strokeDasharray: "2.2 1.6",
    strokeLinecap: "round",
  };

  return (
    <svg
      viewBox="0 0 200 380"
      className={className}
      role="img"
      aria-label={label}
    >
      <defs>
        <clipPath id={`${p}-clip`}>
          <path d={leg} />
          <path d={leg} transform="translate(200 0) scale(-1 1)" />
        </clipPath>
        <linearGradient id={`${p}-shade`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity="0.38" />
          <stop offset="0.16" stopColor="#000" stopOpacity="0.06" />
          <stop offset="0.33" stopColor="#000" stopOpacity="0" />
          <stop offset="0.5" stopColor="#000" stopOpacity="0.22" />
          <stop offset="0.67" stopColor="#000" stopOpacity="0" />
          <stop offset="0.84" stopColor="#000" stopOpacity="0.06" />
          <stop offset="1" stopColor="#000" stopOpacity="0.38" />
        </linearGradient>
        <linearGradient id={`${p}-drop`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#000" stopOpacity="0.18" />
          <stop offset="0.12" stopColor="#000" stopOpacity="0" />
          <stop offset="0.9" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.14" />
        </linearGradient>
        <radialGradient id={`${p}-fade`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#fff" stopOpacity={isJeans ? 0.32 : 0.08} />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <pattern id={`${p}-twill`} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
          <line x1="0" y1="0" x2="0" y2="4" stroke="#fff" strokeOpacity={isJeans ? 0.09 : 0.04} strokeWidth="1.4" />
        </pattern>
        <linearGradient id={`${p}-wood`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#9a6844" />
          <stop offset="1" stopColor="#5c3822" />
        </linearGradient>
        <linearGradient id={`${p}-metal`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#8d8f93" />
          <stop offset="0.5" stopColor="#f2f3f5" />
          <stop offset="1" stopColor="#8d8f93" />
        </linearGradient>
      </defs>

      {/* hanger hook + wooden bar */}
      <path d="M100,26 L100,14 C100,4 112,2 113,9 C113.5,12 111,14 109,13" fill="none" stroke={`url(#${p}-metal)`} strokeWidth="3" strokeLinecap="round" />
      <rect x="34" y="24" width="132" height="9" rx="4.5" fill={`url(#${p}-wood)`} />
      <rect x="47" y="30" width="9" height="22" rx="2" fill={`url(#${p}-metal)`} />
      <rect x="144" y="30" width="9" height="22" rx="2" fill={`url(#${p}-metal)`} />

      {/* the fabric, everything below is clipped to the trouser shape */}
      <g clipPath={`url(#${p}-clip)`}>
        <rect x="0" y="40" width="200" height="340" fill={wash} />
        <ellipse cx="68" cy="170" rx="36" ry="80" fill={`url(#${p}-fade)`} />
        <ellipse cx="132" cy="170" rx="36" ry="80" fill={`url(#${p}-fade)`} />
        {isJeans && <ellipse cx="100" cy="300" rx="90" ry="40" fill={`url(#${p}-fade)`} opacity="0.5" />}
        <rect x="0" y="40" width="200" height="340" fill={`url(#${p}-twill)`} />
        <rect x="0" y="40" width="200" height="340" fill={`url(#${p}-shade)`} />
        <rect x="0" y="40" width="200" height="340" fill={`url(#${p}-drop)`} />

        {/* waistband */}
        <rect x="0" y="44" width="200" height="16" fill="#000" opacity="0.12" />
        <line x1="0" y1="57" x2="200" y2="57" {...stitchProps} />
        <line x1="0" y1="47" x2="200" y2="47" {...stitchProps} />

        {/* fly */}
        <path d={`M112,60 L112,${isJeans ? 118 : 112} Q112,${isJeans ? 130 : 124} 100,${isJeans ? 134 : 128}`} {...stitchProps} />
        <line x1="100" y1="60" x2="100" y2="150" stroke="#000" strokeOpacity="0.25" strokeWidth="1" />

        {/* front pockets */}
        <path d="M74,60 Q72,94 40,102" {...stitchProps} />
        <path d="M126,60 Q128,94 160,102" {...stitchProps} />
        <path d="M74,60 Q72,94 40,102" fill="none" stroke="#000" strokeOpacity="0.2" strokeWidth="0.8" transform="translate(-1.5 -1)" />
        <path d="M126,60 Q128,94 160,102" fill="none" stroke="#000" strokeOpacity="0.2" strokeWidth="0.8" transform="translate(1.5 -1)" />
        {isJeans && <path d="M132,64 L148,64 L149,80 Q140,83 131,80 Z" {...stitchProps} />}

        {/* whiskers */}
        {isJeans && (
          <g stroke="#fff" strokeOpacity="0.22" strokeWidth="1.6" strokeLinecap="round" fill="none">
            <path d="M88,140 Q76,138 64,144" />
            <path d="M90,148 Q80,148 70,154" />
            <path d="M112,140 Q124,138 136,144" />
            <path d="M110,148 Q120,148 130,154" />
          </g>
        )}

        {/* pressed crease or pleats */}
        {(fit === "pleated" || fit === "slim") && (
          <g stroke="#000" strokeOpacity="0.18" strokeWidth="1">
            <line x1="70" y1="60" x2={hemMid} y2={HEM_Y} />
            <line x1="130" y1="60" x2={200 - hemMid} y2={HEM_Y} />
          </g>
        )}
        {fit === "pleated" && (
          <g stroke="#000" strokeOpacity="0.28" strokeWidth="1.2">
            <line x1="80" y1="60" x2="81" y2="96" />
            <line x1="88" y1="60" x2="88" y2="84" />
            <line x1="120" y1="60" x2="119" y2="96" />
            <line x1="112" y1="60" x2="112" y2="84" />
          </g>
        )}

        {/* cargo pockets */}
        {fit === "cargo" && (
          <g>
            {[0, 1].map((side) => (
              <g key={side} transform={side ? "translate(200 0) scale(-1 1)" : undefined}>
                <rect x="30" y="198" width="42" height="56" rx="3" fill="#000" fillOpacity="0.08" />
                <rect x="30" y="198" width="42" height="56" rx="3" {...stitchProps} />
                <rect x="28" y="192" width="46" height="16" rx="3" fill={wash} stroke="#000" strokeOpacity="0.2" />
              </g>
            ))}
          </g>
        )}

        {/* carpenter hammer loop + side pocket */}
        {fit === "carpenter" && (
          <g>
            <rect x="140" y="112" width="22" height="84" rx="2" fill="#000" fillOpacity="0.06" />
            <rect x="140" y="112" width="22" height="84" rx="2" {...stitchProps} />
            <rect x="30" y="170" width="16" height="10" fill="#000" fillOpacity="0.12" />
            <rect x="30" y="170" width="16" height="10" {...stitchProps} />
          </g>
        )}

        {/* hem */}
        <line x1="0" y1={HEM_Y - 9} x2="200" y2={HEM_Y - 9} {...stitchProps} />
        <rect x="0" y={HEM_Y - 6} width="200" height="10" fill="#000" opacity="0.08" />
      </g>

      {/* belt loops + button sit on top of the fabric */}
      {[52, 80, 120, 148].map((x) => (
        <rect key={x} x={x - 3} y="42" width="6" height="20" rx="1.5" fill={wash} stroke="#000" strokeOpacity="0.25" strokeWidth="0.8" />
      ))}
      <circle cx="110" cy="52" r="4.2" fill={isJeans ? `url(#${p}-metal)` : "#2b2b2b"} stroke="#000" strokeOpacity="0.3" strokeWidth="0.6" />

      {/* hanger clips bite into the waistband */}
      <rect x="46" y="40" width="11" height="12" rx="2" fill={`url(#${p}-metal)`} stroke="#000" strokeOpacity="0.2" strokeWidth="0.5" />
      <rect x="143" y="40" width="11" height="12" rx="2" fill={`url(#${p}-metal)`} stroke="#000" strokeOpacity="0.2" strokeWidth="0.5" />
    </svg>
  );
}

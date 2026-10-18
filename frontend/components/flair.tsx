/* Decorative pieces for the "duel across time" look: VS medallion, orrery, knowledge graph, edition timeline. */

export function VsMedallion({ size = 76, className = "" }: { size?: number; className?: string }) {
  return (
    <span
      className={`relative inline-flex shrink-0 items-center justify-center rounded-full ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <span className="vs-ring absolute inset-0 rounded-full opacity-90 blur-[6px]" />
      <span className="vs-ring absolute inset-0 rounded-full" />
      <span
        className="relative flex items-center justify-center rounded-full bg-[#0c0b12] font-fell italic text-white shadow-inner"
        style={{ width: size - 6, height: size - 6, fontSize: size * 0.38 }}
      >
        vs
      </span>
    </span>
  );
}

/** Copperplate-style solar system (a nod to Plate XL of the 1771 edition), planets slowly orbiting. */
export function Orrery({ className = "" }: { className?: string }) {
  const orbits = [
    { r: 42, d: 14, p: 3 },
    { r: 70, d: 22, p: 3.5 },
    { r: 100, d: 34, p: 4 },
    { r: 132, d: 50, p: 4.5 },
    { r: 166, d: 74, p: 6 },
    { r: 200, d: 110, p: 5 },
  ];
  return (
    <svg viewBox="-220 -220 440 440" className={className} aria-hidden>
      <defs>
        <radialGradient id="sun">
          <stop offset="0" stopColor="#fff1cf" />
          <stop offset="0.5" stopColor="#f0c070" />
          <stop offset="1" stopColor="#b4532a" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle r="34" fill="url(#sun)" opacity="0.65" />
      <circle r="12" fill="#f5d08a" />
      {orbits.map((o, i) => (
        <g key={o.r}>
          <circle r={o.r} fill="none" stroke="#f0c070" strokeOpacity={0.28} strokeWidth="0.8" />
          <circle r={o.r} fill="none" stroke="#f0c070" strokeOpacity={0.12} strokeWidth="0.6" strokeDasharray="1 4" transform="scale(1.03)" />
          <g
            className="orbit"
            style={{ animationDuration: `${o.d}s`, animationDelay: `-${(i * 7.3) % o.d}s` }}
          >
            <circle cx={o.r} r={o.p} fill="#f5d08a" />
            <circle cx={o.r} r={o.p + 4} fill="#f0c070" opacity="0.18" />
          </g>
        </g>
      ))}
    </svg>
  );
}

/** Linked-knowledge network: glowing nodes and flowing edges. */
const NODES: [number, number][] = [
  [40, 60], [120, 30], [210, 70], [300, 40], [370, 110], [80, 150], [170, 140], [260, 160],
  [340, 210], [50, 250], [140, 230], [230, 250], [310, 300], [110, 320], [200, 330], [380, 330],
];
const EDGES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [1, 6], [2, 6], [2, 7], [3, 7], [4, 8], [5, 6], [6, 7], [7, 8],
  [5, 9], [5, 10], [6, 10], [7, 11], [10, 11], [8, 12], [11, 12], [9, 13], [10, 13], [11, 14], [13, 14],
  [12, 15], [14, 12],
];

export function KnowledgeNet({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 420 370" className={className} aria-hidden>
      {EDGES.map(([a, b], i) => (
        <line
          key={i}
          x1={NODES[a][0]}
          y1={NODES[a][1]}
          x2={NODES[b][0]}
          y2={NODES[b][1]}
          stroke={i % 3 ? "#7dd3fc" : "#a5b4fc"}
          strokeOpacity="0.35"
          strokeWidth="1"
          className={i % 4 === 0 ? "edge-flow" : undefined}
        />
      ))}
      {NODES.map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r={i % 5 === 0 ? 6 : 3.5} fill={i % 2 ? "#38bdf8" : "#818cf8"} className="node-pulse" style={{ animationDelay: `${(i * 0.37) % 3.2}s` }} />
          <circle cx={x} cy={y} r="1.6" fill="#f0f9ff" />
        </g>
      ))}
    </svg>
  );
}

/* ------------------------------ icons ------------------------------ */

export function SwordsIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={`h-4 w-4 fill-none stroke-current ${className}`} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2M9.5 6.5 13 3h3v3l-3.5 3.5M5 14l4 4M7 17l-3 3M3 19l2 2" />
    </svg>
  );
}

export function QuestionIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={`h-4 w-4 fill-none stroke-current ${className}`} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="9.5" />
      <path d="M9.2 9.2a2.9 2.9 0 0 1 5.6 1c0 1.9-2.8 2.6-2.8 4.3M12 17.6h.01" />
    </svg>
  );
}

export function DossierIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={`h-4 w-4 fill-none stroke-current ${className}`} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v1M3 7v11a2 2 0 0 0 2 2h6" />
      <circle cx="17" cy="16" r="3.5" />
      <path d="m19.6 18.6 2.4 2.4" />
    </svg>
  );
}

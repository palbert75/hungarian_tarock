/** The polgármester's hat: a black cylinder with a gold band and a plume of feathers. */
export default function MayorHat({ title }: { title: string }) {
  return (
    <span className="mayor-hat" title={title} aria-label={title} role="img">
      <svg viewBox="0 0 36 34" width="36" height="34" aria-hidden="true">
        {/* feathers tucked into the band, behind the crown */}
        <path d="M22 22 C 22 12, 27 4, 35 1 C 30 6, 27 13, 25.5 22 Z" fill="#ef4444" stroke="#7f1d1d" strokeWidth="0.6" />
        <path d="M21 22 C 19 13, 21 5, 26 0 C 24 6, 23.5 13, 24 22 Z" fill="#f8fafc" stroke="#94a3b8" strokeWidth="0.6" />
        <path d="M23.5 22 C 26 15, 30 11, 36 10 C 31 13, 28 17, 26.5 22.5 Z" fill="#22c55e" stroke="#14532d" strokeWidth="0.6" />
        <path d="M27 7 L 32 4 M 26.5 12 L 31.5 9.5" stroke="#7f1d1d" strokeWidth="0.4" opacity="0.6" />
        {/* the cylinder: crown, top and brim */}
        <path d="M8 5 L 24 5 L 23 26 L 9 26 Z" fill="#111827" stroke="#475569" strokeWidth="0.7" />
        <ellipse cx="16" cy="5" rx="8" ry="1.8" fill="#1f2937" stroke="#475569" strokeWidth="0.7" />
        <path d="M8.6 9 L 23.4 9" stroke="#ffffff" strokeWidth="0.8" opacity="0.15" />
        <rect x="8.8" y="20" width="14.4" height="3.2" fill="#facc15" />
        <ellipse cx="16" cy="27" rx="14" ry="2.8" fill="#111827" stroke="#facc15" strokeWidth="0.8" />
        {/* cockade on the band */}
        <circle cx="12.5" cy="21.6" r="2.4" fill="#dc2626" stroke="#fff" strokeWidth="0.8" />
        <circle cx="12.5" cy="21.6" r="0.9" fill="#16a34a" />
      </svg>
    </span>
  )
}

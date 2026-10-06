export default function Logo({ size = 26, light = false }: { size?: number; light?: boolean }) {
  // A finish-line chevron: an upright bar and an arrow pointing to the line.
  return (
    <span className={`logo${light ? " light" : ""}`}>
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="4" fill="#FC5200" />
        <path d="M8 8h4.5v16H8z" fill="#fff" />
        <path d="M15.5 8L25 16l-9.5 8v-5l3.6-3-3.6-3z" fill="#fff" />
      </svg>
      <span className="wordmark">Iron Coach</span>
    </span>
  );
}

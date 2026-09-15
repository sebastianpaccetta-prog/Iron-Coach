export default function Logo({ size = 28 }: { size?: number }) {
  // Original mark: a stylised "IC" finish-line chevron in the brand orange.
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-label="Iron Coach logo" role="img">
      <rect x="1" y="1" width="30" height="30" rx="8" fill="#F26522" />
      <path d="M8 9h4v14H8z" fill="#fff" />
      <path d="M15 9l9 7-9 7v-4.5l4-2.5-4-2.5z" fill="#fff" />
    </svg>
  );
}

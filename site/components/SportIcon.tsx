const PATHS: Record<string, React.ReactNode> = {
  swim: (
    <>
      <circle cx="17" cy="6" r="2" />
      <path d="M5 13l5-4 3 3.5 4-2.5" />
      <path d="M2 17.5c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5" />
      <path d="M2 21.5c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5" />
    </>
  ),
  bike: (
    <>
      <circle cx="5.5" cy="16.5" r="3.5" />
      <circle cx="18.5" cy="16.5" r="3.5" />
      <path d="M5.5 16.5L9 9h7l2.5 7.5M9 9l3.5 7.5H5.5M14.5 5.5h2.5L16 9" />
    </>
  ),
  run: (
    <>
      <circle cx="15.5" cy="4" r="2" />
      <path d="M8 21l3-5 3 2v-5" />
      <path d="M5 11l3-3 4-1 2 3 3 2 3-1" />
      <path d="M12 7l2 6-2 3" />
    </>
  ),
  strength: <path d="M6 7v10M18 7v10M3 9.5v5M21 9.5v5M6 12h12" />,
  rest: <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />,
  race: <path d="M5 21V3.5M5 4h12l-2.5 4L17 12H5" />,
  other: <path d="M3 12h4l3-7 4 14 3-7h4" />,
};

export default function SportIcon({ sport, size = 20 }: { sport: string; size?: number }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-label={sport} role="img"
    >
      {PATHS[sport] ?? PATHS.other}
    </svg>
  );
}

/**
 * Soft wellness gradient blobs used as a page backdrop (auth + landing).
 * Purely decorative; sits behind content and works in light and dark mode.
 */
export function GradientBlobs() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div className="absolute -left-24 -top-32 h-96 w-96 rounded-full bg-brand-blue/25 blur-3xl" />
      <div className="absolute -right-28 top-1/4 h-96 w-96 rounded-full bg-brand-violet/25 blur-3xl" />
      <div className="absolute -bottom-32 left-1/3 h-96 w-96 rounded-full bg-brand-green/20 blur-3xl" />
    </div>
  );
}

export function normalizeOverlayValues(values: Record<string, number | null | undefined>): Record<string, number | null> {
  const finite = Object.values(values).filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  const minimum = finite.length ? Math.min(...finite) : null; const maximum = finite.length ? Math.max(...finite) : null;
  return Object.fromEntries(Object.entries(values).map(([id, value]) => {
    if (typeof value !== "number" || !Number.isFinite(value) || minimum === null || maximum === null) return [id, null];
    return [id, minimum === maximum ? 0.5 : (value - minimum) / (maximum - minimum)];
  }));
}

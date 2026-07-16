import type { ScenarioDraft } from "../scenarios/builders";

export function renameScenario(items: ScenarioDraft[], id: string, name: string): ScenarioDraft[] {
  if (!name.trim()) return items;
  return items.map((item) => item.id === id ? { ...item, name } : item);
}

export function duplicateScenario(
  items: ScenarioDraft[],
  id: string,
  createId: () => string = () => globalThis.crypto?.randomUUID?.() ?? `scenario-${Date.now()}`,
): ScenarioDraft[] {
  if (items.length >= 3) return items;
  const index = items.findIndex((item) => item.id === id);
  if (index < 0) return items;
  let nextId = createId();
  while (items.some((item) => item.id === nextId)) nextId = createId();
  const source = items[index];
  const copy = { ...source, id: nextId, name: `${source.name.trim()} copy` };
  return [...items.slice(0, index + 1), copy, ...items.slice(index + 1)];
}

export function deleteScenario(items: ScenarioDraft[], id: string): ScenarioDraft[] {
  return items.filter((item) => item.id !== id);
}

export function moveScenario(items: ScenarioDraft[], id: string, direction: -1 | 1): ScenarioDraft[] {
  const from = items.findIndex((item) => item.id === id);
  const to = from + direction;
  if (from < 0 || to < 0 || to >= items.length) return items;
  const next = [...items];
  [next[from], next[to]] = [next[to], next[from]];
  return next;
}

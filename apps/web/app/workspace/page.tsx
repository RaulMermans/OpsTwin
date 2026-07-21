import { Workspace } from "./workspace";

export type WorkspaceMode = "guided" | "advanced";

export function resolveInitialMode(value: string | string[] | undefined): WorkspaceMode {
  const candidate = Array.isArray(value) ? value[0] : value;
  return candidate === "advanced" ? "advanced" : "guided";
}

export default async function WorkspacePage({ searchParams }: { searchParams: Promise<{ mode?: string | string[] }> }) {
  const resolved = await searchParams;
  return <Workspace initialMode={resolveInitialMode(resolved.mode)} />;
}

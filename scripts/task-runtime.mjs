import { delimiter, dirname } from "node:path";

export function nodeExecutable() {
  return process.execPath;
}

export function childEnvironment(environment = process.env) {
  const pathEntries = Object.entries(environment).filter(
    ([key]) => key.toLowerCase() === "path",
  );
  const currentPath = pathEntries.at(-1)?.[1] ?? "";
  const normalized = Object.fromEntries(
    Object.entries(environment).filter(([key]) => key.toLowerCase() !== "path"),
  );
  return {
    ...normalized,
    PATH: [dirname(process.execPath), currentPath].filter(Boolean).join(delimiter),
  };
}

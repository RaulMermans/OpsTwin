import type { NormalizationResult, NormalizationWarning, PlaybackEvent, PlaybackEventType, PlaybackSelection, PlaybackSource } from "./types";

type UnknownRecord = Record<string, unknown>;
const asRecord = (value: unknown): UnknownRecord | null => typeof value === "object" && value !== null && !Array.isArray(value) ? value as UnknownRecord : null;
const asString = (value: unknown): string | null => typeof value === "string" ? value : null;
const asFiniteNumber = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null;

const KNOWN_EVENT_TYPES: PlaybackEventType[] = [
  "ITEM_CREATED", "QUEUE_ENTERED", "RESOURCE_REQUESTED", "PROCESS_STARTED",
  "PROCESS_COMPLETED", "RESOURCE_RELEASED", "ROUTE_SELECTED", "ITEM_FAILED",
  "ITEM_REWORKED", "ITEM_COMPLETED",
];

function summarize(eventType: PlaybackEventType, event: UnknownRecord): string {
  const item = asString(event.itemId) ?? "unknown item";
  const stage = asString(event.stageId);
  const resource = asString(event.resourcePoolId);
  const route = asString(event.routeId);
  const target = asString(event.targetId);
  switch (eventType) {
    case "ITEM_CREATED": return `Item ${item} arrived`;
    case "QUEUE_ENTERED": return `Item ${item} entered the queue${stage ? ` at stage ${stage}` : ""}`;
    case "RESOURCE_REQUESTED": return `Item ${item} requested a unit of ${resource ?? "a resource pool"}`;
    case "PROCESS_STARTED": return `Item ${item} began processing${stage ? ` at stage ${stage}` : ""}`;
    case "PROCESS_COMPLETED": return `Item ${item} completed processing${stage ? ` at stage ${stage}` : ""}`;
    case "RESOURCE_RELEASED": return `Item ${item} released a unit of ${resource ?? "a resource pool"}`;
    case "ROUTE_SELECTED": return `Item ${item} selected route ${route ?? "unknown"}${target ? ` toward ${target}` : ""}`;
    case "ITEM_REWORKED": return `Item ${item} entered rework`;
    case "ITEM_FAILED": return `Item ${item} reached terminal failure`;
    case "ITEM_COMPLETED": return `Item ${item} reached terminal completion`;
    default: return `Unrecognized event for item ${item}`;
  }
}

/**
 * Pure adapter: raw retained representative events -> normalized playback events.
 * Never mutates the source array or its objects.
 */
export function normalizeEvents(rawEvents: unknown[]): NormalizationResult {
  const warnings: NormalizationWarning[] = [];
  const seenIds = new Set<string>();
  const staged: (PlaybackEvent & { sourceIndex: number })[] = [];

  rawEvents.forEach((raw, sourceIndex) => {
    const event = asRecord(raw);
    if (!event) return;
    const simulationTime = asFiniteNumber(event.simulationTime);
    if (simulationTime === null) {
      warnings.push({ code: "non_finite_time", detail: `Event at source index ${sourceIndex} has a non-finite simulationTime and was excluded.` });
      return;
    }
    const rawType = asString(event.eventType);
    const eventType: PlaybackEventType = rawType && (KNOWN_EVENT_TYPES as string[]).includes(rawType) ? rawType as PlaybackEventType : "UNKNOWN";
    if (rawType && eventType === "UNKNOWN") {
      warnings.push({ code: "unknown_event_type", detail: `Event at source index ${sourceIndex} has unrecognized eventType "${rawType}"; kept as a generic event.` });
    }
    const itemId = asString(event.itemId);
    if (itemId === null) {
      warnings.push({ code: "missing_item_id", detail: `Event at source index ${sourceIndex} has no itemId and was excluded.` });
      return;
    }
    const sequence = asFiniteNumber(event.sequence);
    const id = sequence !== null ? String(sequence) : `idx:${sourceIndex}`;
    if (seenIds.has(id)) {
      warnings.push({ code: "duplicate_event_id", detail: `Event at source index ${sourceIndex} duplicates event ID "${id}" and was excluded.` });
      return;
    }
    seenIds.add(id);

    staged.push({
      id,
      index: -1,
      simulationTime,
      eventType,
      itemId,
      stageId: asString(event.stageId),
      resourcePoolId: asString(event.resourcePoolId),
      routeId: asString(event.routeId),
      targetId: asString(event.targetId),
      sampledDuration: asFiniteNumber(event.sampledDuration),
      summary: summarize(eventType, event),
      sourceIndex,
    });
  });

  staged.sort((a, b) => a.simulationTime - b.simulationTime || a.sourceIndex - b.sourceIndex);
  const events = staged.map((event, index) => ({ ...event, index }));
  return { events, warnings };
}

/**
 * Pure adapter: one RepresentativeVariantResult-shaped record (baseline or
 * scenario) -> a typed PlaybackSource, or null when required evidence is
 * absent (e.g. the representative was never retained).
 */
export function extractRepresentativeSource(
  variant: "baseline" | "scenario",
  variantResult: unknown,
  scenarioName: string | null,
  modelHash: string | null,
): PlaybackSource | null {
  const outer = asRecord(variantResult);
  const representative = asRecord(outer?.representative);
  const result = asRecord(representative?.result);
  if (!outer || !representative || !result) return null;

  const runIndex = asFiniteNumber(representative.runIndex);
  const seed = asFiniteNumber(representative.seed);
  const selectionMethod = asString(representative.selectionMethod);
  const detailMode = asString(representative.detailMode);
  const events = result.events;
  if (runIndex === null || seed === null || !selectionMethod || detailMode === null || !Array.isArray(events)) return null;

  const observationRecord = asRecord(result.observation);
  const resultDetail = asRecord(result.resultDetail);
  const selectedItemIds = Array.isArray(resultDetail?.selectedItemIds)
    ? resultDetail.selectedItemIds.filter((item): item is string => typeof item === "string")
    : [];

  const selection: PlaybackSelection = {
    variant,
    variantId: asString(outer.variantId) ?? variant,
    runIndex,
    seed,
    selectionMethod,
    distance: asFiniteNumber(representative.distance) ?? 0,
    detailMode: (detailMode === "summary" || detailMode === "sampled" || detailMode === "full") ? detailMode : "sampled",
    includedEventCount: asFiniteNumber(representative.includedEventCount) ?? events.length,
    modelHash,
    scenarioName,
    observation: observationRecord && asFiniteNumber(observationRecord.measurementStart) !== null && asFiniteNumber(observationRecord.measurementEnd) !== null
      ? {
          measurementStart: asFiniteNumber(observationRecord.measurementStart) as number,
          measurementEnd: asFiniteNumber(observationRecord.measurementEnd) as number,
          measurementDuration: asFiniteNumber(observationRecord.measurementDuration) ?? 0,
        }
      : null,
    selectedItemIds,
  };

  return { selection, events };
}

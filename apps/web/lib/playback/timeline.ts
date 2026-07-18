import type { NormalizationWarning, PlaybackEvent, PlaybackFrame, PlaybackTimeline, ResourceOccupancy, StageOccupancy, TimelineCheckpoint } from "./types";

function emptyFrame(simulationTime: number): PlaybackFrame {
  return {
    simulationTime,
    eventIndex: -1,
    eventsAtTime: [],
    stages: [],
    resources: [],
    completedItemIds: [],
    failedItemIds: [],
    reworkingItemIds: [],
    integrityWarnings: [],
  };
}

function sortedArray(set: Set<string>): string[] {
  return [...set].sort();
}

function toStageOccupancy(waiting: Map<string, Set<string>>, processing: Map<string, Set<string>>): StageOccupancy[] {
  const stageIds = new Set<string>([...waiting.keys(), ...processing.keys()]);
  return [...stageIds].sort().map((stageId) => ({
    stageId,
    waitingItemIds: sortedArray(waiting.get(stageId) ?? new Set()),
    processingItemIds: sortedArray(processing.get(stageId) ?? new Set()),
  }));
}

function toResourceOccupancy(busy: Map<string, Set<string>>): ResourceOccupancy[] {
  return [...busy.keys()].sort().map((resourcePoolId) => ({
    resourcePoolId,
    busyItemIds: sortedArray(busy.get(resourcePoolId) ?? new Set()),
  }));
}

/**
 * Pure adapter: normalized events -> a deterministic timeline with one
 * checkpoint frame per distinct simulationTime. Seeking is bounded to a
 * binary search over checkpoints rather than replaying from event zero.
 */
export function buildTimeline(events: PlaybackEvent[], warnings: NormalizationWarning[] = []): PlaybackTimeline {
  const waiting = new Map<string, Set<string>>();
  const processing = new Map<string, Set<string>>();
  const busy = new Map<string, Set<string>>();
  const completed = new Set<string>();
  const failed = new Set<string>();
  const reworking = new Set<string>();
  const integrityWarnings: string[] = [];

  function addTo(map: Map<string, Set<string>>, key: string | null, itemId: string) {
    if (!key) return;
    if (!map.has(key)) map.set(key, new Set());
    map.get(key)!.add(itemId);
  }
  function removeFrom(map: Map<string, Set<string>>, key: string | null, itemId: string) {
    if (!key) return;
    map.get(key)?.delete(itemId);
  }
  function removeEverywhere(itemId: string) {
    for (const set of waiting.values()) set.delete(itemId);
    for (const set of processing.values()) set.delete(itemId);
    for (const set of busy.values()) set.delete(itemId);
  }

  const checkpoints: TimelineCheckpoint[] = [];
  let groupStart = 0;
  while (groupStart < events.length) {
    let groupEnd = groupStart;
    const time = events[groupStart].simulationTime;
    while (groupEnd < events.length && events[groupEnd].simulationTime === time) groupEnd++;
    const group = events.slice(groupStart, groupEnd);

    for (const event of group) {
      const itemId = event.itemId;
      if (!itemId) continue;
      switch (event.eventType) {
        case "QUEUE_ENTERED":
          addTo(waiting, event.stageId, itemId);
          break;
        case "PROCESS_STARTED":
          removeFrom(waiting, event.stageId, itemId);
          addTo(processing, event.stageId, itemId);
          addTo(busy, event.resourcePoolId, itemId);
          break;
        case "PROCESS_COMPLETED":
          removeFrom(processing, event.stageId, itemId);
          break;
        case "RESOURCE_RELEASED":
          removeFrom(busy, event.resourcePoolId, itemId);
          break;
        case "ITEM_REWORKED":
          reworking.add(itemId);
          break;
        case "ITEM_FAILED":
          removeEverywhere(itemId);
          reworking.delete(itemId);
          failed.add(itemId);
          break;
        case "ITEM_COMPLETED":
          removeEverywhere(itemId);
          reworking.delete(itemId);
          completed.add(itemId);
          break;
        case "ITEM_CREATED":
        case "RESOURCE_REQUESTED":
        case "ROUTE_SELECTED":
        case "UNKNOWN":
          break;
      }
    }

    checkpoints.push({
      eventIndex: groupEnd - 1,
      simulationTime: time,
      frame: {
        simulationTime: time,
        eventIndex: groupEnd - 1,
        eventsAtTime: group,
        stages: toStageOccupancy(waiting, processing),
        resources: toResourceOccupancy(busy),
        completedItemIds: sortedArray(completed),
        failedItemIds: sortedArray(failed),
        reworkingItemIds: sortedArray(reworking),
        integrityWarnings: [...integrityWarnings],
      },
    });
    groupStart = groupEnd;
  }

  return {
    events,
    checkpoints,
    warnings,
    minTime: events.length ? events[0].simulationTime : 0,
    maxTime: events.length ? events[events.length - 1].simulationTime : 0,
  };
}

/** Binary search for the last checkpoint at or before `atTime`. */
function checkpointIndexAtOrBefore(timeline: PlaybackTimeline, atTime: number): number {
  const { checkpoints } = timeline;
  let low = 0;
  let high = checkpoints.length - 1;
  let result = -1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (checkpoints[mid].simulationTime <= atTime) {
      result = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return result;
}

/**
 * Deterministic pure reconstruction: (timeline, time) -> frame. Seeking to
 * the same time always returns an equal frame (GM-131).
 */
export function buildFrame(timeline: PlaybackTimeline, atTime: number): PlaybackFrame {
  const index = checkpointIndexAtOrBefore(timeline, atTime);
  if (index === -1) return emptyFrame(atTime);
  const checkpoint = timeline.checkpoints[index];
  if (checkpoint.simulationTime === atTime) return checkpoint.frame;
  return { ...checkpoint.frame, simulationTime: atTime, eventsAtTime: [] };
}

export function checkpointAtIndex(timeline: PlaybackTimeline, checkpointIndex: number): TimelineCheckpoint | null {
  return timeline.checkpoints[checkpointIndex] ?? null;
}

/** Convenience wrapper used by the controller UI: -1 is the initial (pre-event) frame. */
export function frameAtCheckpointIndex(timeline: PlaybackTimeline, checkpointIndex: number): PlaybackFrame {
  if (checkpointIndex < 0) return emptyFrame(timeline.minTime);
  return timeline.checkpoints[checkpointIndex]?.frame ?? emptyFrame(timeline.minTime);
}

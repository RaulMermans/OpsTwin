import type { ImportantEvent, PlaybackTimeline } from "./types";

/**
 * Derive factual "important events" from the reconstructed checkpoints only
 * (never inferred, never labelled "critical" beyond this documented set).
 */
export function deriveImportantEvents(timeline: PlaybackTimeline, resourceCapacities: Record<string, number>): ImportantEvent[] {
  const important: ImportantEvent[] = [];
  // Starts at 0 (not -1): a run where no queue ever forms should report no
  // "maximum queue reached" event at all, not a trivial "0 items" one.
  let maxQueue = 0;
  const wasFullyUtilized = new Set<string>();

  for (const checkpoint of timeline.checkpoints) {
    const totalWaiting = checkpoint.frame.stages.reduce((sum, stage) => sum + stage.waitingItemIds.length, 0);
    if (totalWaiting > maxQueue) {
      maxQueue = totalWaiting;
      important.push({
        category: "maximum_sampled_queue_reached",
        simulationTime: checkpoint.simulationTime,
        eventIndex: checkpoint.eventIndex,
        summary: `Maximum sampled queue: ${totalWaiting} item${totalWaiting === 1 ? "" : "s"} at time ${checkpoint.simulationTime}.`,
      });
    }

    for (const resource of checkpoint.frame.resources) {
      const capacity = resourceCapacities[resource.resourcePoolId];
      if (capacity === undefined || capacity <= 0) continue;
      const isFull = resource.busyItemIds.length >= capacity;
      const wasFull = wasFullyUtilized.has(resource.resourcePoolId);
      if (isFull && !wasFull) {
        wasFullyUtilized.add(resource.resourcePoolId);
        important.push({
          category: "resource_fully_utilized",
          simulationTime: checkpoint.simulationTime,
          eventIndex: checkpoint.eventIndex,
          resourcePoolId: resource.resourcePoolId,
          summary: `${resource.resourcePoolId} reached full utilization at time ${checkpoint.simulationTime}.`,
        });
      } else if (!isFull && wasFull) {
        wasFullyUtilized.delete(resource.resourcePoolId);
        important.push({
          category: "resource_no_longer_fully_utilized",
          simulationTime: checkpoint.simulationTime,
          eventIndex: checkpoint.eventIndex,
          resourcePoolId: resource.resourcePoolId,
          summary: `${resource.resourcePoolId} stopped being fully utilized at time ${checkpoint.simulationTime}.`,
        });
      }
    }

    for (const event of checkpoint.frame.eventsAtTime) {
      if (event.eventType === "ITEM_REWORKED") {
        important.push({ category: "rework_started", simulationTime: event.simulationTime, eventIndex: event.index, summary: `Item ${event.itemId} entered rework at time ${event.simulationTime}.` });
      } else if (event.eventType === "ITEM_FAILED") {
        important.push({ category: "item_failed", simulationTime: event.simulationTime, eventIndex: event.index, summary: `Item ${event.itemId} failed at time ${event.simulationTime}.` });
      } else if (event.eventType === "ITEM_COMPLETED") {
        important.push({ category: "item_completed", simulationTime: event.simulationTime, eventIndex: event.index, summary: `Item ${event.itemId} completed at time ${event.simulationTime}.` });
      }
    }
  }

  return important;
}

export function nextImportantEventIndex(important: ImportantEvent[], afterEventIndex: number): number | null {
  const next = important.find((item) => item.eventIndex > afterEventIndex);
  return next ? next.eventIndex : null;
}

export function previousImportantEventIndex(important: ImportantEvent[], beforeEventIndex: number): number | null {
  let found: number | null = null;
  for (const item of important) {
    if (item.eventIndex < beforeEventIndex) found = item.eventIndex;
    else break;
  }
  return found;
}

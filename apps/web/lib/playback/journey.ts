import type { ItemJourney, JourneyVisit, PlaybackTimeline } from "./types";

/**
 * Pure adapter: reconstruct one sampled item's ordered journey entirely from
 * the normalized event log. Repeated stage visits (rework loops) remain
 * distinct entries; nothing is collapsed or invented.
 */
export function buildItemJourney(timeline: PlaybackTimeline, itemId: string, slaTargetDuration: number | null): ItemJourney {
  const events = timeline.events.filter((event) => event.itemId === itemId);
  const visits: JourneyVisit[] = [];
  const routeDecisions: ItemJourney["routeDecisions"] = [];
  let arrivalTime: number | null = null;
  let completedAt: number | null = null;
  let failedAt: number | null = null;
  let reworkCount = 0;
  let open: JourneyVisit | null = null;

  function closeOpenVisit() {
    if (open) {
      visits.push(open);
      open = null;
    }
  }

  for (const event of events) {
    switch (event.eventType) {
      case "ITEM_CREATED":
        arrivalTime = event.simulationTime;
        break;
      case "QUEUE_ENTERED":
        closeOpenVisit();
        open = {
          visitNumber: visits.length + 1,
          stageId: event.stageId ?? "unknown",
          resourcePoolId: null,
          queueEnteredAt: event.simulationTime,
          processStartedAt: null,
          processCompletedAt: null,
          waitingDuration: null,
          processingDuration: null,
          reworked: false,
        };
        break;
      case "PROCESS_STARTED":
        if (open) {
          open.processStartedAt = event.simulationTime;
          open.resourcePoolId = event.resourcePoolId ?? open.resourcePoolId;
          open.waitingDuration = open.queueEnteredAt !== null ? event.simulationTime - open.queueEnteredAt : null;
        }
        break;
      case "PROCESS_COMPLETED":
        if (open) {
          open.processCompletedAt = event.simulationTime;
          open.processingDuration = open.processStartedAt !== null ? event.simulationTime - open.processStartedAt : null;
        }
        closeOpenVisit();
        break;
      case "ROUTE_SELECTED":
        routeDecisions.push({ routeId: event.routeId ?? "unknown", targetId: event.targetId, simulationTime: event.simulationTime });
        break;
      case "ITEM_REWORKED":
        reworkCount += 1;
        if (visits.length > 0) visits[visits.length - 1].reworked = true;
        else if (open) open.reworked = true;
        break;
      case "ITEM_FAILED":
        closeOpenVisit();
        failedAt = event.simulationTime;
        break;
      case "ITEM_COMPLETED":
        closeOpenVisit();
        completedAt = event.simulationTime;
        break;
      default:
        break;
    }
  }
  closeOpenVisit();

  const terminalTime = completedAt ?? failedAt;
  const cycleTime = arrivalTime !== null && terminalTime !== null ? terminalTime - arrivalTime : null;
  const slaResult: ItemJourney["slaResult"] =
    slaTargetDuration === null || cycleTime === null || failedAt !== null
      ? failedAt !== null ? "violated" : "not_available"
      : cycleTime <= slaTargetDuration ? "attained" : "violated";

  return {
    itemId,
    arrivalTime,
    visits,
    routeDecisions,
    reworkCount,
    completedAt,
    failedAt,
    cycleTime,
    slaResult,
    slaTargetDuration,
  };
}

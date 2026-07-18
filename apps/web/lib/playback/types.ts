export type PlaybackEventType =
  | "ITEM_CREATED"
  | "QUEUE_ENTERED"
  | "RESOURCE_REQUESTED"
  | "PROCESS_STARTED"
  | "PROCESS_COMPLETED"
  | "RESOURCE_RELEASED"
  | "ROUTE_SELECTED"
  | "ITEM_FAILED"
  | "ITEM_REWORKED"
  | "ITEM_COMPLETED"
  | "UNKNOWN";

export interface PlaybackEvent {
  id: string;
  index: number;
  simulationTime: number;
  eventType: PlaybackEventType;
  itemId: string | null;
  stageId: string | null;
  resourcePoolId: string | null;
  routeId: string | null;
  targetId: string | null;
  sampledDuration: number | null;
  summary: string;
  sourceIndex: number;
}

export interface NormalizationWarning {
  code: "non_finite_time" | "duplicate_event_id" | "unknown_event_type" | "missing_item_id";
  detail: string;
}

export interface NormalizationResult {
  events: PlaybackEvent[];
  warnings: NormalizationWarning[];
}

export interface PlaybackSelection {
  variant: "baseline" | "scenario";
  variantId: string;
  runIndex: number;
  seed: number;
  selectionMethod: string;
  distance: number;
  detailMode: "summary" | "sampled" | "full";
  includedEventCount: number;
  modelHash: string | null;
  scenarioName: string | null;
  observation: {
    measurementStart: number;
    measurementEnd: number;
    measurementDuration: number;
  } | null;
  selectedItemIds: string[];
}

export interface PlaybackSource {
  selection: PlaybackSelection;
  events: unknown[];
}

export interface StageOccupancy {
  stageId: string;
  waitingItemIds: string[];
  processingItemIds: string[];
}

export interface ResourceOccupancy {
  resourcePoolId: string;
  busyItemIds: string[];
}

export interface PlaybackFrame {
  simulationTime: number;
  eventIndex: number;
  eventsAtTime: PlaybackEvent[];
  stages: StageOccupancy[];
  resources: ResourceOccupancy[];
  completedItemIds: string[];
  failedItemIds: string[];
  reworkingItemIds: string[];
  integrityWarnings: string[];
}

export interface TimelineCheckpoint {
  eventIndex: number;
  simulationTime: number;
  frame: PlaybackFrame;
}

export interface PlaybackTimeline {
  events: PlaybackEvent[];
  checkpoints: TimelineCheckpoint[];
  warnings: NormalizationWarning[];
  minTime: number;
  maxTime: number;
}

export type ImportantEventCategory =
  | "maximum_sampled_queue_reached"
  | "resource_fully_utilized"
  | "resource_no_longer_fully_utilized"
  | "rework_started"
  | "item_failed"
  | "item_completed"
  | "sla_violation";

export interface ImportantEvent {
  category: ImportantEventCategory;
  simulationTime: number;
  eventIndex: number;
  summary: string;
}

export interface JourneyVisit {
  visitNumber: number;
  stageId: string;
  resourcePoolId: string | null;
  queueEnteredAt: number | null;
  processStartedAt: number | null;
  processCompletedAt: number | null;
  waitingDuration: number | null;
  processingDuration: number | null;
  reworked: boolean;
}

export interface ItemJourney {
  itemId: string;
  arrivalTime: number | null;
  visits: JourneyVisit[];
  routeDecisions: { routeId: string; targetId: string | null; simulationTime: number }[];
  reworkCount: number;
  completedAt: number | null;
  failedAt: number | null;
  cycleTime: number | null;
  slaResult: "attained" | "violated" | "not_available";
  slaTargetDuration: number | null;
}

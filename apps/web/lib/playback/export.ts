import type { ItemJourney, NormalizationWarning, PlaybackEvent, PlaybackSelection } from "./types";

export interface PlaybackExport {
  exportVersion: 1;
  sourceType: "baseline" | "scenario";
  scenarioId: string;
  runIndex: number;
  seed: number;
  selectionMethod: string;
  observationWindow: PlaybackSelection["observation"];
  events: PlaybackEvent[];
  temporalSummary: string[];
  itemJourneys: ItemJourney[];
  integrityWarnings: NormalizationWarning[];
}

/**
 * Client-side export payload. Excludes browser timer/React state,
 * filesystem paths, stack traces, and secrets by construction — it is
 * built only from already-normalized, already-safe playback evidence.
 */
export function buildPlaybackExport(
  selection: PlaybackSelection,
  events: PlaybackEvent[],
  temporalSummary: string[],
  itemJourneys: ItemJourney[],
  integrityWarnings: NormalizationWarning[],
): PlaybackExport {
  return {
    exportVersion: 1,
    sourceType: selection.variant,
    scenarioId: selection.variantId,
    runIndex: selection.runIndex,
    seed: selection.seed,
    selectionMethod: selection.selectionMethod,
    observationWindow: selection.observation,
    events,
    temporalSummary,
    itemJourneys,
    integrityWarnings,
  };
}

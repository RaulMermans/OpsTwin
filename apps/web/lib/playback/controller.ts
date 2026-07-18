export type PlaybackSpeed = 0.5 | 1 | 2 | 4;

export interface PlaybackState {
  /** -1 means "before the first event" (the initial/restart state). */
  checkpointIndex: number;
  playing: boolean;
  speed: PlaybackSpeed;
}

export type PlaybackAction =
  | { type: "play" }
  | { type: "pause" }
  | { type: "restart" }
  | { type: "stepForward" }
  | { type: "stepBackward" }
  | { type: "seek"; checkpointIndex: number }
  | { type: "setSpeed"; speed: PlaybackSpeed }
  | { type: "tick" };

export function initialPlaybackState(): PlaybackState {
  return { checkpointIndex: -1, playing: false, speed: 1 };
}

const BASE_INTERVAL_MS = 600;
export function intervalMsForSpeed(speed: PlaybackSpeed): number {
  return BASE_INTERVAL_MS / speed;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Pure playback state machine. `checkpointCount` is the number of
 * precomputed timeline checkpoints (see timeline.ts); it is passed in
 * rather than stored so the reducer stays a pure function of its inputs.
 */
export function playbackReducer(state: PlaybackState, action: PlaybackAction, checkpointCount: number): PlaybackState {
  const lastIndex = checkpointCount - 1;
  switch (action.type) {
    case "play": {
      if (checkpointCount === 0) return state;
      const atEnd = state.checkpointIndex >= lastIndex;
      return { ...state, playing: true, checkpointIndex: atEnd ? -1 : state.checkpointIndex };
    }
    case "pause":
      return { ...state, playing: false };
    case "restart":
      return { ...state, playing: false, checkpointIndex: -1 };
    case "stepForward":
      return { ...state, playing: false, checkpointIndex: clamp(state.checkpointIndex + 1, -1, lastIndex) };
    case "stepBackward":
      return { ...state, playing: false, checkpointIndex: clamp(state.checkpointIndex - 1, -1, lastIndex) };
    case "seek":
      return { ...state, playing: false, checkpointIndex: clamp(action.checkpointIndex, -1, lastIndex) };
    case "setSpeed":
      return { ...state, speed: action.speed };
    case "tick": {
      if (!state.playing || checkpointCount === 0) return state;
      const next = state.checkpointIndex + 1;
      if (next > lastIndex) return { ...state, playing: false, checkpointIndex: lastIndex };
      return { ...state, checkpointIndex: next };
    }
    default:
      return state;
  }
}

import { describe, expect, it } from "vitest";

import { initialPlaybackState, intervalMsForSpeed, playbackReducer } from "../lib/playback/controller";

const CHECKPOINTS = 5; // indices 0..4, lastIndex = 4

describe("playbackReducer", () => {
  it("play starts playback from the initial state", () => {
    const state = playbackReducer(initialPlaybackState(), { type: "play" }, CHECKPOINTS);
    expect(state.playing).toBe(true);
    expect(state.checkpointIndex).toBe(-1);
  });

  it("pause stops playback without moving the checkpoint", () => {
    const playing = playbackReducer(initialPlaybackState(), { type: "play" }, CHECKPOINTS);
    const paused = playbackReducer(playing, { type: "pause" }, CHECKPOINTS);
    expect(paused.playing).toBe(false);
    expect(paused.checkpointIndex).toBe(playing.checkpointIndex);
  });

  it("restart returns to the initial state and pauses", () => {
    let state = initialPlaybackState();
    state = playbackReducer(state, { type: "seek", checkpointIndex: 3 }, CHECKPOINTS);
    state = playbackReducer(state, { type: "play" }, CHECKPOINTS);
    state = playbackReducer(state, { type: "restart" }, CHECKPOINTS);
    expect(state).toEqual({ checkpointIndex: -1, playing: false, speed: 1 });
  });

  it("step forward advances exactly one checkpoint and pauses", () => {
    const state = playbackReducer({ checkpointIndex: 1, playing: true, speed: 1 }, { type: "stepForward" }, CHECKPOINTS);
    expect(state).toMatchObject({ checkpointIndex: 2, playing: false });
  });

  it("step backward moves exactly one checkpoint back and pauses", () => {
    const state = playbackReducer({ checkpointIndex: 2, playing: true, speed: 1 }, { type: "stepBackward" }, CHECKPOINTS);
    expect(state).toMatchObject({ checkpointIndex: 1, playing: false });
  });

  it("step forward and backward are exact inverses around an interior index", () => {
    const start = { checkpointIndex: 2, playing: false, speed: 1 as const };
    const forward = playbackReducer(start, { type: "stepForward" }, CHECKPOINTS);
    const back = playbackReducer(forward, { type: "stepBackward" }, CHECKPOINTS);
    expect(back.checkpointIndex).toBe(start.checkpointIndex);
  });

  it("step forward clamps at the last checkpoint", () => {
    const state = playbackReducer({ checkpointIndex: 4, playing: false, speed: 1 }, { type: "stepForward" }, CHECKPOINTS);
    expect(state.checkpointIndex).toBe(4);
  });

  it("step backward clamps at the initial state", () => {
    const state = playbackReducer({ checkpointIndex: -1, playing: false, speed: 1 }, { type: "stepBackward" }, CHECKPOINTS);
    expect(state.checkpointIndex).toBe(-1);
  });

  it("seek clamps into range and pauses playback", () => {
    const state = playbackReducer({ checkpointIndex: 0, playing: true, speed: 1 }, { type: "seek", checkpointIndex: 999 }, CHECKPOINTS);
    expect(state).toMatchObject({ checkpointIndex: 4, playing: false });
    const belowRange = playbackReducer({ checkpointIndex: 0, playing: true, speed: 1 }, { type: "seek", checkpointIndex: -50 }, CHECKPOINTS);
    expect(belowRange.checkpointIndex).toBe(-1);
  });

  it("speed change never alters the checkpoint index or event ordering", () => {
    const state = playbackReducer({ checkpointIndex: 2, playing: true, speed: 1 }, { type: "setSpeed", speed: 4 }, CHECKPOINTS);
    expect(state).toEqual({ checkpointIndex: 2, playing: true, speed: 4 });
  });

  it("supports the four documented speeds", () => {
    expect(intervalMsForSpeed(0.5)).toBeGreaterThan(intervalMsForSpeed(1));
    expect(intervalMsForSpeed(1)).toBeGreaterThan(intervalMsForSpeed(2));
    expect(intervalMsForSpeed(2)).toBeGreaterThan(intervalMsForSpeed(4));
  });

  it("tick advances playback by one checkpoint while playing", () => {
    const state = playbackReducer({ checkpointIndex: 1, playing: true, speed: 1 }, { type: "tick" }, CHECKPOINTS);
    expect(state.checkpointIndex).toBe(2);
  });

  it("tick does nothing while paused", () => {
    const state = playbackReducer({ checkpointIndex: 1, playing: false, speed: 1 }, { type: "tick" }, CHECKPOINTS);
    expect(state.checkpointIndex).toBe(1);
  });

  it("playback pauses automatically at the end state", () => {
    const state = playbackReducer({ checkpointIndex: 4, playing: true, speed: 1 }, { type: "tick" }, CHECKPOINTS);
    expect(state).toMatchObject({ checkpointIndex: 4, playing: false });
  });

  it("play after reaching the end restarts from the beginning", () => {
    const atEnd = { checkpointIndex: 4, playing: false, speed: 1 as const };
    const state = playbackReducer(atEnd, { type: "play" }, CHECKPOINTS);
    expect(state).toMatchObject({ checkpointIndex: -1, playing: true });
  });

  it("play with zero checkpoints is a no-op", () => {
    const state = playbackReducer(initialPlaybackState(), { type: "play" }, 0);
    expect(state.playing).toBe(false);
  });
});

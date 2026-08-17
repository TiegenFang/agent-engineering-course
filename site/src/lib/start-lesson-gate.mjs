/**
 * W1 lesson completion gate (v3 spec D6): a lesson is complete when the
 * learner has (1) answered the pre-track predictions, (2) visited all four
 * loop-track stations, and (3) answered all knowledge-check questions
 * correctly.
 *
 * Each contributing section on the page marks its own progress with a
 * `data-start-gate="<kind>"` element whose `data-done` attribute is "1"
 * (satisfied) or "0" (not yet).  Sections announce changes by dispatching a
 * {@link START_GATE_EVENT} custom event that bubbles to `document`; the gate
 * UI in AgentLoopTrack listens and re-evaluates.  This module deliberately
 * holds only DOM reads and pure helpers so it can be unit-tested with a
 * minimal stub root.
 */

/** Custom event name dispatched whenever one of the gate flags changes. */
export const START_GATE_EVENT = "start-gate-change";

/**
 * @typedef {Object<string, boolean>} GateState
 * @property {boolean} predict
 * @property {boolean} track
 * @property {boolean} quiz
 */

/** Gate kinds in learner-facing order. */
export const startGateKinds = ["predict", "track", "quiz"];

/** Learner-facing labels, also used to list what is still missing. */
export const startGateLabels = {
  predict: "预测题已作答",
  track: "跑道完整跑过一圈（到达过全部四站）",
  quiz: "知识检查 3 题全对",
};

const isDone = (root, kind) =>
  root.querySelector(`[data-start-gate="${kind}"]`)?.getAttribute("data-done") === "1";

/**
 * Read the current gate state from the page.  Missing sections count as
 * unsatisfied, so a page that never mounts one condition can never be
 * marked complete by accident.
 *
 * @param {{ querySelector?: (selector: string) => { getAttribute?: (name: string) => string | null } | null }} root
 * @returns {GateState}
 */
export function readStartGate(root = document) {
  const state = {};
  for (const kind of startGateKinds) {
    state[kind] = isDone(root, kind);
  }
  return state;
}

/** Labels of the conditions that are not satisfied yet.
 * @param {GateState} state
 * @returns {string[]}
 */
export function missingGateItems(state) {
  return startGateKinds.filter((kind) => !state[kind]).map((kind) => startGateLabels[kind]);
}

/** Whether every gate condition is satisfied.
 * @param {GateState} state
 * @returns {boolean}
 */
export function isGateSatisfied(state) {
  return startGateKinds.every((kind) => state[kind]);
}

/** How many conditions are satisfied right now (for "n/3" feedback).
 * @param {GateState} state
 * @returns {number}
 */
export function countGateDone(state) {
  return startGateKinds.filter((kind) => state[kind]).length;
}

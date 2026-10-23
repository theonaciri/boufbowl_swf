// Run from /probe.html?replay=1 served by tools.smoke_possession_client.
const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export async function checkPossessionTiming(rates = [25, 60, 120, 240]) {
  const player = document.querySelector('ruffle-player');
  const call = (rate) => player.ruffle().callExternalInterface('probePossessionLive', rate);
  const ready = call(0);
  if (!ready?.ready) throw new Error('Wait for the tactical field to load, then retry.');
  const rows = [];
  for (const rate of rates) {
    call(rate);
    await delay(100);
    const samples = [];
    for (let index = 0; index < 3; index++) {
      await delay(200);
      const sample = call(0);
      if (!sample?.state) throw new Error('The Ruffle diagnostic callback did not return a view.');
      const state = sample.state;
      sample.expectedFrame = 1 + Math.floor((state.elapsed + state.updatedAt - state.started) / 40) % state.totalFrames;
      sample.frameSelectionCorrect = state.frame === sample.expectedFrame;
      sample.renderAgeMs = state.sampledAt - state.updatedAt;
      if (!sample.frameSelectionCorrect || sample.stageRate !== rate || !state.running || !state.front || !state.back) {
        throw new Error(`Possession clock failed at ${rate} FPS: ${JSON.stringify(sample)}`);
      }
      samples.push(sample);
    }
    rows.push({ target: rate, samples });
  }
  return rows;
}

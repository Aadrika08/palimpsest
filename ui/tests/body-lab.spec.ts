import {test, expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

// An external supervised server supplies real owners; this test never substitutes physics.
test('actual calibrated body manual controls, snapshot, reset and action replay', async ({page}, info) => {
  test.skip(process.env.PALIMPSEST_BODY_LAB_TESTS !== '1', 'Opt-in actual CPU/EGL owner and browser gate.');
  const owners: string[] = [], closes: any[] = [], observations: any[] = [], browserErrors: string[] = [];
  const report: any = {version: 1, status: 'running', owners, closes, observations, browser_errors: browserErrors,
    test_sha256: createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex'),
    protocol: {owners: 2, scenario: 'calibrated-wheel-compensation', keyboard: {velocity: .3, heading: .2},
      initial_zero_steps: 1, reset_zero_steps: 1, replay: 'actions', timeout_seconds: 180},
    scope: 'Actual manual loaded-calibration UI mechanism and replay; no online adaptation, task, drift or physical qualification.'};
  page.on('pageerror', error => browserErrors.push(error.message));
  async function request(path: string, body?: unknown) {
    return page.evaluate(async ({path, body}) => {
      const token = (await (await fetch('/api/v1/session')).json()).token;
      const response = await fetch('/api/v1' + path, {method: body === undefined ? 'GET' : 'POST',
        headers: {'X-Palimpsest-Session': token, 'Content-Type': 'application/json'},
        ...(body === undefined ? {} : {body: JSON.stringify(body)})});
      return {status: response.status, value: await response.json()};
    }, {path, body});
  }
  async function get(path: string) {const result = await request(path); expect(result.status).toBe(200); return result.value;}
  async function latestAppliedAction(id: string) {
    const events = (await get(`/runs/${id}/events?after=0&limit=200`)).events;
    const command = events.filter((event: any) => event.kind === 'command_received' && event.command.kind === 'set_action').at(-1)?.command;
    return events.some((event: any) => event.kind === 'command_applied' && event.id === command?.id) ? command.payload.action : null;
  }
  async function clickClose(id: string) {
    const pending = page.waitForResponse(response => response.url().endsWith(`/runs/${id}/close`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Close run', exact: true}).click();
    const response = await pending, value = await response.json(); closes.push({run_id: id, status: response.status(), value});
    expect(response.status()).toBe(200); expect(value).toMatchObject({run_id: id, status: 'closed'});
    await expect(page.getByRole('button', {name: 'Close run', exact: true})).toBeDisabled();
  }
  try {
    await page.goto('/'); await expect(page.getByRole('button', {name: 'Create run', exact: true})).toBeEnabled();
    expect((await get('/runs')).runs).toEqual([]); // Fresh dedicated run root required.
    await page.getByLabel('Scenario', {exact: true}).selectOption('calibrated-wheel-compensation');
    await expect(page.getByLabel('Scenario', {exact: true}).locator('option:checked')).toHaveText('Calibrated wheel compensation (development)');
    for (const [label, value] of [['Controller', 'manual'], ['Inference device', 'cpu'], ['Texture', 'checker']]) {
      await expect(page.getByLabel(label, {exact: true})).toHaveValue(value);
    }
    await expect(page.getByLabel('Controller', {exact: true}).locator('option[value="teacher"]')).toHaveJSProperty('disabled', true);
    await expect(page.getByLabel('Inference device', {exact: true}).locator('option[value="cuda"]')).toHaveJSProperty('disabled', true);
    await page.getByLabel('Seed', {exact: true}).fill('1');
    const creating = page.waitForResponse(response => response.url().endsWith('/api/v1/runs') && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Create run', exact: true}).click();
    const created = await creating; expect(created.status()).toBe(202); const source = (await created.json()).run_id; owners.push(source);
    await expect(page.getByRole('button', {name: 'Step', exact: true})).toBeEnabled({timeout: 60_000});
    const initial = await get(`/runs/${source}`); expect(initial.state).toMatchObject({controller: 'manual', scenario: 'calibrated-wheel-compensation', total_tick: 0, phase: 'paused'});
    expect(initial.state.body.phase).toBe('loaded');
    await page.getByRole('button', {name: 'Step', exact: true}).click();
    await expect.poll(async () => (await get(`/runs/${source}`)).state.total_tick).toBe(1);
    const manual = page.locator('.manual-pad');
    for (const [key, action] of [['ArrowUp', [.3, 0]], ['ArrowDown', [-.3, 0]], ['ArrowLeft', [0, .2]], ['ArrowRight', [0, -.2]]] as const) {
      await manual.focus(); await page.keyboard.down(key);
      await expect.poll(() => latestAppliedAction(source)).toEqual(action);
      expect((await get(`/runs/${source}`)).state.total_tick).toBe(1); // Intent does not step while paused.
      await page.keyboard.up(key); await expect.poll(() => latestAppliedAction(source)).toEqual([0, 0]);
    }
    await page.getByRole('button', {name: 'Start', exact: true}).click();
    await expect(page.locator('.run-heading strong')).toHaveText('running');
    await manual.focus(); await page.keyboard.down('ArrowUp');
    await expect.poll(() => latestAppliedAction(source)).toEqual([.3, 0]);
    await expect.poll(async () => (await get(`/runs/${source}`)).sample?.transition?.control).toEqual([.7532490491867065, .6210575103759766]);
    await page.keyboard.up('ArrowUp'); await page.getByRole('button', {name: 'Pause', exact: true}).click();
    await expect(page.locator('.run-heading strong')).toHaveText('paused');
    const paused = await get(`/runs/${source}`); expect(paused.state.body.phase).toBe('compensating'); observations.push({stage: 'paused', state: paused.state, transition: paused.sample?.transition});
    const capturing = page.waitForResponse(response => response.url().endsWith(`/runs/${source}/snapshot`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Capture snapshot', exact: true}).click();
    const captured = await capturing; expect(captured.status()).toBe(200); report.snapshot_id = (await captured.json()).snapshot_id;
    await expect(page.getByLabel('Snapshot', {exact: true})).toHaveValue(report.snapshot_id);
    await expect(page.getByLabel('Branch controller', {exact: true}).locator('option[value="teacher"]')).toHaveJSProperty('disabled', true);
    await page.getByRole('button', {name: 'Reset', exact: true}).click();
    await expect.poll(async () => (await get(`/runs/${source}`)).state.episode).toBe(1);
    const reset = await get(`/runs/${source}`); expect(reset.state.total_tick).toBe(paused.state.total_tick); expect(reset.state.body).toMatchObject({phase: 'loaded', last_tick: null, previous_angles_rad: [0, 0], time_s: 0});
    observations.push({stage: 'reset', state: reset.state});
    await page.getByRole('button', {name: 'Step', exact: true}).click();
    await expect.poll(async () => (await get(`/runs/${source}`)).state.total_tick).toBe(paused.state.total_tick + 1);
    await expect.poll(async () => (await get(`/runs/${source}`)).sample?.transition?.episode).toBe(1);
    const final = await get(`/runs/${source}`); expect(final.sample.transition.control).toEqual([0, 0]); report.source_ticks = final.state.total_tick;
    await page.screenshot({path: info.outputPath('body-paused.png')});
    await clickClose(source);
    await page.getByLabel('Recorded run', {exact: true}).selectOption(source);
    const replaying = page.waitForResponse(response => response.url().endsWith(`/runs/${source}/replay`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Action replay', exact: true}).click();
    const response = await replaying; expect(response.status()).toBe(202); const replay = (await response.json()).run_id; owners.push(replay);
    await expect.poll(async () => (await get(`/runs/${replay}`)).jobstate, {timeout: 60_000}).toBe('completed');
    const done = await get(`/runs/${replay}`); expect(done.replay.status).toBe('passed'); expect(done.replay.compared_ticks).toBe(report.source_ticks); report.replay = done.replay;
    await expect(page.locator('.mode')).toHaveText('Action replay');
    await page.screenshot({path: info.outputPath('body-action-replay.png')});
    const replayClose = await request(`/runs/${replay}/close`, {}); closes.push({run_id: replay, ...replayClose, transport: 'HTTP after completed replay'});
    expect(replayClose.status).toBe(200); expect(replayClose.value).toMatchObject({run_id: replay, status: 'closed'});
    expect(browserErrors).toEqual([]); await expect(page.getByRole('alert')).toHaveCount(0); report.status = 'passed';
  } catch (error) {report.status = 'failed'; report.error = String(error); throw error;}
  finally {
    const cleanup: any[] = []; report.cleanup = cleanup;
    for (const id of [...owners].reverse()) {
      try {cleanup.push({run_id: id, ...await request(`/runs/${id}/close`, {})});}
      catch (error) {cleanup.push({run_id: id, error: String(error)});}
    }
    const clean = cleanup.every(item => item.status === 200 && item.value?.status === 'closed');
    if (!clean) report.status = 'failed';
    await writeFile(info.outputPath('body-lab-report.json'), JSON.stringify(report, null, 2) + '\n');
    await info.attach('body-lab-report.json', {body: JSON.stringify(report, null, 2), contentType: 'application/json'});
    expect(clean, 'Every created owner must explicitly close normally').toBe(true);
  }
});

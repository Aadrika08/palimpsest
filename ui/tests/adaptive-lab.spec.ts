import {test, expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

// Existing body-lab transport/cleanup pattern; every owner uses actual CPU/EGL physics.
test('actual adaptive calibration probes, fitted manual drive, reset and action replay', async ({page}, info) => {
  test.skip(process.env.PALIMPSEST_ADAPTIVE_LAB_TESTS !== '1', 'Opt-in actual CPU/EGL calibration and browser gate.');
  const owners: string[] = [], closes: any[] = [], observations: any[] = [], browserErrors: string[] = [];
  const report: any = {version: 1, status: 'running', owners, closes, observations, browser_errors: browserErrors,
    test_sha256: createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex'),
    protocol: {owners: 2, scenario: 'adaptive-wheel-calibration', seed: 1, probes: 4, ticks_per_probe: 120,
      next_commands: 4, fit_samples: 400, keyboard_velocity: .3, maximum_source_ticks: 600,
      maximum_fitted_ticks: 60, absolute_source_interval_ceiling: 1081,
      replay: 'actions', timeout_seconds: 180},
    scope: 'Actual manual measured-calibration UI mechanisms; one authored simulator fixture, no held-out task, neural learning or physical qualification.'};
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
  async function clickClose(id: string) {
    const pending = page.waitForResponse(response => response.url().endsWith(`/runs/${id}/close`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Close run', exact: true}).click();
    const response = await pending, value = await response.json(); closes.push({run_id: id, status: response.status(), value});
    expect(response.status()).toBe(200); expect(value).toMatchObject({run_id: id, status: 'closed'});
    await expect(page.getByRole('button', {name: 'Close run', exact: true})).toBeDisabled();
  }
  try {
    await page.goto('/'); await expect(page.getByRole('button', {name: 'Create run', exact: true})).toBeEnabled();
    expect((await get('/runs')).runs).toEqual([]);
    await page.getByLabel('Scenario', {exact: true}).selectOption('adaptive-wheel-calibration');
    await expect(page.getByLabel('Scenario', {exact: true}).locator('option:checked')).toHaveText('Measured wheel calibration (development)');
    for (const [label, value] of [['Controller', 'manual'], ['Inference device', 'cpu'], ['Texture', 'checker']]) {
      await expect(page.getByLabel(label, {exact: true})).toHaveValue(value);
    }
    await expect(page.getByLabel('Controller', {exact: true}).locator('option[value="teacher"]')).toHaveJSProperty('disabled', true);
    await expect(page.getByLabel('Inference device', {exact: true}).locator('option[value="cuda"]')).toHaveJSProperty('disabled', true);
    await expect(page.getByLabel('Seed', {exact: true})).toHaveValue('1');
    await expect(page.getByLabel('Seed', {exact: true})).toBeDisabled();
    const creating = page.waitForResponse(response => response.url().endsWith('/api/v1/runs') && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Create run', exact: true}).click();
    const created = await creating; expect(created.status()).toBe(202); const source = (await created.json()).run_id; owners.push(source);
    await expect(page.getByRole('button', {name: 'Step', exact: true})).toBeEnabled({timeout: 60_000});
    const calibration = page.getByRole('region', {name: 'Measured calibration'}), manual = page.locator('.manual-pad');
    await expect(manual).toBeDisabled();
    for (let trial = 0; trial < 4; trial++) {
      const fresh = await get(`/runs/${source}`);
      expect(fresh.state).toMatchObject({phase: 'paused', episode: trial, episode_step: 0, total_tick: trial * 120});
      expect(fresh.state.body).toMatchObject({phase: 'collecting', trial_index: trial, sample_count: trial * 100});
      await expect(manual).toBeDisabled();
      await expect(calibration.getByRole('button')).toBeDisabled();
      await page.getByRole('button', {name: 'Start', exact: true}).click();
      await expect.poll(async () => (await get(`/runs/${source}`)).state.episode_step, {timeout: 30_000}).toBe(120);
      await expect(page.locator('.run-heading strong')).toHaveText('paused');
      const completed = await get(`/runs/${source}`);
      expect(completed.state.body).toMatchObject({phase: trial === 3 ? 'fit_complete' : 'trial_complete',
        trial_index: trial, sample_count: (trial + 1) * 100, episode_step: 120});
      observations.push({stage: `probe-${trial + 1}`, state: completed.state});
      await expect(manual).toBeDisabled();
      await expect(page.getByRole('button', {name: 'Step', exact: true})).toBeDisabled();
      await expect(calibration).toContainText(`${(trial + 1) * 100} retained measurements`);
      if (trial === 3) {
        expect(completed.state.body.gains_rad_s_per_control).toHaveLength(2);
        report.fit_sha256 = completed.state.body.fit_sha256;
        report.samples_sha256 = completed.state.body.samples_sha256;
      }
      await calibration.getByRole('button', {name: trial === 3 ? 'Start fitted episode' : 'Next calibration trial', exact: true}).click();
      await expect.poll(async () => (await get(`/runs/${source}`)).state.episode).toBe(trial + 1);
    }
    const fitted = await get(`/runs/${source}`);
    expect(fitted.state.body).toMatchObject({phase: 'fitted', sample_count: 400, episode_step: 0,
      fit_sha256: report.fit_sha256, samples_sha256: report.samples_sha256});
    await expect(calibration).toContainText('Fitted episode'); await expect(manual).toBeEnabled();
    await calibration.getByText('Calibration progress', {exact: true}).click();
    await expect(calibration).toContainText(String(fitted.state.body.gains_rad_s_per_control[0]));
    // Expected effective control uses visible measured gains and pinned nominal response,
    // never pose feedback. Driver remains one fixed nominal keyboard command.
    const nominal = Math.fround(Math.fround(.3) * 2), reference = [14.878897911022118, 14.878897948225164];
    report.expected_fitted_control = reference.map((gain, i) => Math.fround(nominal * (gain / fitted.state.body.gains_rad_s_per_control[i])));
    await page.getByRole('button', {name: 'Step', exact: true}).click();
    await expect.poll(async () => (await get(`/runs/${source}`)).state.episode_step).toBe(1);
    await page.getByRole('button', {name: 'Start', exact: true}).click();
    await expect(page.locator('.run-heading strong')).toHaveText('running');
    await manual.focus(); await page.keyboard.down('ArrowUp');
    await expect.poll(async () => (await get(`/runs/${source}`)).sample?.transition?.control).toEqual(report.expected_fitted_control);
    await page.keyboard.up('ArrowUp'); await page.getByRole('button', {name: 'Pause', exact: true}).click();
    await expect(page.locator('.run-heading strong')).toHaveText('paused');
    const paused = await get(`/runs/${source}`);
    expect(paused.state.body).toMatchObject({phase: 'fitted', sample_count: 400, fit_sha256: report.fit_sha256, samples_sha256: report.samples_sha256});
    expect(paused.state.episode_step).toBeGreaterThan(1); expect(paused.state.episode_step).toBeLessThanOrEqual(60);
    observations.push({stage: 'fitted-paused', state: paused.state, transition: paused.sample?.transition});
    const capturing = page.waitForResponse(response => response.url().endsWith(`/runs/${source}/snapshot`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Capture snapshot', exact: true}).click();
    const captured = await capturing; expect(captured.status()).toBe(200); report.snapshot_id = (await captured.json()).snapshot_id;
    await expect(page.getByLabel('Snapshot', {exact: true})).toHaveValue(report.snapshot_id);
    await page.screenshot({path: info.outputPath('adaptive-fitted.png')});
    await page.getByRole('button', {name: 'Reset', exact: true}).click();
    await expect.poll(async () => (await get(`/runs/${source}`)).state.episode).toBe(5);
    const reset = await get(`/runs/${source}`);
    expect(reset.state.total_tick).toBe(paused.state.total_tick);
    expect(reset.state.body).toMatchObject({phase: 'collecting', trial_index: 0, sample_count: 0, episode_step: 0,
      fit_sha256: null, gains_rad_s_per_control: null});
    await expect(manual).toBeDisabled(); observations.push({stage: 'reset-cleared', state: reset.state});
    await page.getByRole('button', {name: 'Step', exact: true}).click();
    await expect.poll(async () => (await get(`/runs/${source}`)).state.total_tick).toBe(paused.state.total_tick + 1);
    const final = await get(`/runs/${source}`); report.source_ticks = final.state.total_tick;
    expect(report.source_ticks).toBeLessThanOrEqual(600); expect(final.sample.transition.episode).toBe(5);
    expect(final.sample.transition.control).toEqual([.4000000059604645, .4000000059604645]);
    await page.screenshot({path: info.outputPath('adaptive-reset.png')});
    await clickClose(source);
    await page.getByLabel('Recorded run', {exact: true}).selectOption(source);
    const replaying = page.waitForResponse(response => response.url().endsWith(`/runs/${source}/replay`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Action replay', exact: true}).click();
    const response = await replaying; expect(response.status()).toBe(202); const replay = (await response.json()).run_id; owners.push(replay);
    await expect.poll(async () => (await get(`/runs/${replay}`)).jobstate, {timeout: 75_000}).toBe('completed');
    const done = await get(`/runs/${replay}`); expect(done.replay.status).toBe('passed'); expect(done.replay.compared_ticks).toBe(report.source_ticks); report.replay = done.replay;
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
    await writeFile(info.outputPath('adaptive-lab-report.json'), JSON.stringify(report, null, 2) + '\n');
    await info.attach('adaptive-lab-report.json', {body: JSON.stringify(report, null, 2), contentType: 'application/json'});
    expect(clean, 'Every created owner must explicitly close normally').toBe(true);
  }
});

import {test, expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

// Requires the actual pinned bundle and a separately supervised local Lab.
// Four sequential owners, one step and one explicit snapshot each; no retries.
test('actual male profiles, native branch and explicit controller replacement', async ({page}, info) => {
  test.skip(process.env.PALIMPSEST_MALE_LAB_TESTS !== '1', 'Opt-in actual CPU/EGL owner and browser gate.');
  const manifestBytes = readFileSync(new URL('../../data/manifests/male-reduced-policy-v1.json', import.meta.url));
  const manifest = JSON.parse(manifestBytes.toString('utf8'));
  const owners: string[] = [], closes: unknown[] = [], runs: any[] = [], browserErrors: string[] = [];
  const report: Record<string, unknown> = {version: 1, status: 'running', runs, closes, browser_errors: browserErrors,
    test_sha256: createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex'),
    model_manifest_sha256: createHash('sha256').update(manifestBytes).digest('hex'),
    limits: {owners: 4, steps_per_owner: 1, explicit_snapshots_per_owner: 1, test_timeout_seconds: 180},
    scope: 'Actual local CPU Lab/UI integration; no navigation, topology-benefit or biological sensor-mapping claim.'};
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
  async function get(path: string) {
    const result = await request(path); expect(result.status).toBe(200); return result.value;
  }
  async function launch(button: string, endpoint: string) {
    const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1' + endpoint && response.request().method() === 'POST');
    await page.getByRole('button', {name: button, exact: true}).click();
    const response = await pending, value = await response.json();
    expect(response.status()).toBe(202); expect(value.run_id).toMatch(/^[0-9a-f]{32}$/);
    owners.push(value.run_id);
    await expect(page.locator('.identity')).toHaveText('Run ' + value.run_id);
    await expect(page.getByRole('button', {name: 'Step', exact: true})).toBeEnabled({timeout: 45_000});
    await expect(page.locator('.mode')).toHaveText('Live lab');
    return value.run_id as string;
  }
  async function observe(id: string, controller: string, initialTick: number, parent?: string, replacement = false) {
    const initial = await get(`/runs/${id}`);
    expect(initial.state.controller).toBe(controller); expect(initial.state.total_tick).toBe(initialTick);
    expect(initial.state.phase).toBe('paused'); expect(initial.state.scenario).toBe('reproduction');
    await page.getByRole('button', {name: 'Step', exact: true}).click();
    await expect.poll(async () => (await get(`/runs/${id}`)).state.total_tick).toBe(initialTick + 1);
    await expect.poll(async () => (await get(`/runs/${id}`)).sample?.transition?.tick).toBe(initialTick);
    const stepped = await get(`/runs/${id}`);
    expect(stepped.sample.inputs.stage).toBe('used'); expect(stepped.sample.transition.populations).toEqual([]);
    expect(stepped.sample.transition.raw_output).toHaveLength(2);
    expect(stepped.sample.transition.raw_output.every((value: number) => Number.isFinite(value))).toBe(true);
    await expect(page.getByRole('img', {name: 'Actual left eye policy input'})).toBeVisible();
    await expect(page.getByText('Male pilot: authored eye/contact/goal-bearing encoder. No biological sensor mapping or navigation qualification.', {exact: true})).toBeVisible();
    await expect(page.getByText('Unavailable. No neural activity is inferred from behavior.', {exact: true})).toBeVisible();
    await expect.poll(async () => (await get(`/runs/${id}/events?after=0&limit=200`)).events.some((event: any) => event.kind === 'policy_loaded')).toBe(true);
    const events = (await get(`/runs/${id}/events?after=0&limit=200`)).events;
    const policy = events.find((event: any) => event.kind === 'policy_loaded').provenance;
    const identity = policy.policy_identity;
    expect(identity.controller).toBe(controller); expect(identity.variant).toBe(manifest.controllers[controller]);
    expect(identity.profile).toBe(manifest.profile);
    expect(identity.model_manifest_sha256).toBe(report.model_manifest_sha256);
    expect(identity.checkpoint_sha256).toBe(manifest.files[identity.variant + '.pt'].sha256);
    expect(identity.training_report_sha256).toBe(manifest.files['report.json'].sha256);
    for (const [key, value] of Object.entries(identity)) if (key.endsWith('_sha256')) expect(value).toMatch(/^[0-9a-f]{64}$/);
    expect(policy.device).toBe('cpu'); expect(policy.requested_device).toBe('cpu');
    await expect(page.locator('.profile-line')).toContainText(controller);
    await expect(page.locator('.profile-line')).toContainText(identity.topology_sha256);
    const details = page.locator('.inspector details').filter({has: page.getByText('Profile and provenance', {exact: true})});
    if (!await details.evaluate(element => (element as HTMLDetailsElement).open)) await details.locator('summary').click();
    await expect.poll(async () => JSON.parse(await details.locator('pre').innerText()).policy?.policy_identity).toEqual(identity);
    if (parent) {
      expect(events.find((event: any) => event.kind === 'application_restored').parent_run_id).toBe(parent);
      const branched = events.find((event: any) => event.kind === 'branch_created');
      expect(branched.parent_snapshot_id).toBe(runs[0].snapshot_id); expect(branched.controller_replaced).toBe(replacement);
      expect(events.filter((event: any) => event.kind === 'controller_replaced').length).toBe(replacement ? 1 : 0);
      if (replacement) expect(events.find((event: any) => event.kind === 'controller_replaced')).toMatchObject({old: 'male-original', new: 'male-control'});
    }
    const snapshotResponse = page.waitForResponse(response => response.url().endsWith(`/runs/${id}/snapshot`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Capture snapshot', exact: true}).click();
    const captured = await snapshotResponse; expect(captured.status()).toBe(200);
    const snapshot = (await captured.json()).snapshot_id;
    await expect(page.getByLabel('Snapshot', {exact: true})).toHaveValue(snapshot);
    runs.push({run_id: id, controller, initial_tick: initialTick, final_tick: stepped.state.total_tick,
      identity, snapshot_id: snapshot, parent_run_id: parent ?? null, controller_replaced: replacement,
      receipts: stepped.receipts, raw_output: stepped.sample.transition.raw_output,
      lineage_events: events.filter((event: any) => ['application_restored', 'branch_created', 'controller_replaced'].includes(event.kind))});
    await page.screenshot({path: info.outputPath(controller + '-' + runs.length + '.png'), fullPage: true});
    const closing = page.waitForResponse(response => response.url().endsWith(`/runs/${id}/close`) && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Close run', exact: true}).click();
    const response = await closing, closed = await response.json();
    closes.push({run_id: id, status: response.status(), response: closed});
    expect(response.status()).toBe(200); expect(closed).toMatchObject({run_id: id, status: 'closed'});
    await expect(page.getByRole('button', {name: 'Close run', exact: true})).toBeDisabled();
    return {id, snapshot, identity};
  }
  try {
    await page.goto('/');
    await expect(page.getByRole('button', {name: 'Create run', exact: true})).toBeEnabled();
    expect((await get('/runs')).runs).toEqual([]); // Use a fresh dedicated server run root.
    for (const controller of ['male-original', 'male-control']) {
      await expect(page.getByLabel('Controller', {exact: true}).locator(`option[value="${controller}"]`)).toBeEnabled();
      await page.getByLabel('Controller', {exact: true}).selectOption(controller);
      for (const [label, selected] of [['Scenario', 'reproduction'], ['Texture', 'checker'], ['Inference device', 'cpu']]) {
        const select = page.getByLabel(label, {exact: true}); await expect(select).toHaveValue(selected);
        expect(await select.locator('option').evaluateAll((options, selected) => options.every(option => (option as HTMLOptionElement).value === selected || (option as HTMLOptionElement).disabled), selected)).toBe(true);
      }
      const base = {controller, device: 'cpu', scenario: 'reproduction', texture: 'checker', seed: 116};
      for (const invalid of [{device: 'cuda'}, {scenario: 'sparse-navigation'}, {texture: 'realistic'}, {policy_identity: {}}, {checkpoint: '/tmp/not-an-asset'}]) {
        expect((await request('/runs', {...base, ...invalid})).status).toBe(400);
      }
      expect((await get('/runs')).runs).toHaveLength(runs.length);
      await page.getByLabel('Seed', {exact: true}).fill('116');
      await observe(await launch('Create run', '/runs'), controller, 0);
    }
    const source = runs[0];
    for (const replacement of [false, true]) {
      await page.getByLabel('Snapshot', {exact: true}).selectOption(source.snapshot_id);
      await page.getByLabel('Branch controller', {exact: true}).selectOption(replacement ? 'male-control' : '');
      await expect(page.getByText(replacement
        ? 'Controller replacement starts fresh controller state; this is not a full-state matched continuation.'
        : 'Compatible snapshots preserve world and controller state.', {exact: true})).toBeVisible();
      const branch = await observe(await launch('Start branch', '/branches'), replacement ? 'male-control' : 'male-original', 1, source.run_id, replacement);
      expect(branch.identity).toEqual(replacement ? runs[1].identity : source.identity);
    }
    expect(new Set(owners).size).toBe(4); expect(browserErrors).toEqual([]);
    await expect(page.locator('.error')).toHaveCount(0);
    report.status = 'passed';
  } catch (error) {
    report.status = 'failed'; report.error = String(error); throw error;
  } finally {
    // Retain each authoritative close response even after an assertion fails.
    const cleanup: any[] = []; report.cleanup = cleanup;
    for (const id of [...owners].reverse()) {
      try { cleanup.push({run_id: id, ...await request(`/runs/${id}/close`, {})}); }
      catch (error) { cleanup.push({run_id: id, error: String(error)}); }
    }
    const cleanupPassed = cleanup.every(item => item.status === 200 && item.value?.status === 'closed' && item.value?.run_id === item.run_id);
    const workflowPassed = report.status === 'passed';
    if (workflowPassed && !cleanupPassed) report.status = 'failed';
    const body = JSON.stringify(report, null, 2) + '\n';
    await writeFile(info.outputPath('male-lab-verification.json'), body);
    await info.attach('male-lab-verification.json', {body, contentType: 'application/json'});
    if (workflowPassed) expect(cleanupPassed, 'Every owner must retain an authoritative clean close').toBe(true);
  }
});

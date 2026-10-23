import {test, expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync, readFileSync, readdirSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';

// New generated HTML and synthetic 120-second audio; no model inference or historical rerun.
test('generated Choir composition exposes boundaries and plays its declared duration', async ({page, context}) => {
  const repo = resolve(process.cwd(), '..');
  const directory = mkdtempSync(join(tmpdir(), 'choir-composition-'));
  try {
    execFileSync('python3', ['-B', '-c', `
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'tests'))
from test_artwork_encounter import EncounterTests, encounter
fixture = EncounterTests()
files = encounter.read_archive(encounter.ARCHIVE, encounter.ARCHIVE_PIN, lambda: None)
files['counterfactual-choir.wav'] = fixture.wav(compose=True)
files['index.html'] = encounter.encounter_html(files)
for name, raw in files.items():
    (Path(sys.argv[2]) / name).write_bytes(raw)
`, repo, directory]);
    const files = Object.fromEntries(readdirSync(directory).map(name => [name, readFileSync(join(directory, name))]));
    const blocked: string[] = [];
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      const name = url.pathname.slice(1) || 'index.html';
      const contentType = name.endsWith('.wav') ? 'audio/wav' : name.endsWith('.svg') ? 'image/svg+xml' : 'text/html';
      if (url.origin === 'http://choir.invalid' && files[name]) return route.fulfill({body: files[name], contentType});
      blocked.push(url.href);
      return route.abort();
    });
    await page.goto('http://choir.invalid');
    const choir = page.locator('#choir');
    await expect(choir).toContainText('Playback ends after 120 seconds');
    await expect(choir).toContainText('Final episode uses a recorded prefix');
    await choir.getByText('Episode boundaries', {exact: true}).click();
    await expect(choir.locator('tbody tr')).toHaveCount(10);
    await expect(choir.locator('tbody tr').last()).toHaveText('9108–1200–599');
    await page.setViewportSize({width: 390, height: 844});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const audio = choir.locator('audio');
    await audio.scrollIntoViewIfNeeded();
    expect(await audio.evaluate((a: HTMLAudioElement) => a.paused && a.currentTime === 0 && !a.autoplay)).toBe(true);
    await audio.focus(); await page.keyboard.press('Space');
    await expect.poll(() => audio.evaluate((a: HTMLAudioElement) => a.currentTime)).toBeGreaterThan(0);
    await choir.getByRole('button', {name: 'Stop audio and return to start'}).focus();
    await page.keyboard.press('Enter');
    expect(await audio.evaluate((a: HTMLAudioElement) => a.paused && a.currentTime === 0)).toBe(true);
    const result = await audio.evaluate(async (a: HTMLAudioElement) => {
      const started = performance.now();
      const ended = new Promise<void>(resolve => a.addEventListener('ended', () => resolve(), {once: true}));
      await a.play(); await ended;
      return {duration: a.duration, elapsed: (performance.now() - started) / 1000};
    });
    expect(result.duration).toBe(120);
    expect(Math.abs(result.elapsed - 120)).toBeLessThan(2);
    expect(blocked).toEqual([]);
    await test.info().attach('composition-playback.json', {body: JSON.stringify(result), contentType: 'application/json'});
  } finally {
    rmSync(directory, {recursive: true, force: true});
  }
});

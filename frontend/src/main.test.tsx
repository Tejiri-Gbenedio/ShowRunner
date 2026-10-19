// @vitest-environment jsdom
import { act } from 'react';
import React from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './main';
import realOutputs from './fixtures/real-pipeline-output.json';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const owner = '11111111-1111-4111-8111-111111111111';
const run = (state: string, extra: Record<string, unknown> = {}) => ({
  id: '22222222-2222-4222-8222-222222222222', preset_id: 'survival-thriller', state,
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z', ...extra,
});

let container: HTMLDivElement;
let root: Root;
beforeEach(() => {
  container = document.createElement('div'); document.body.appendChild(container);
  localStorage.clear(); vi.stubGlobal('crypto', { randomUUID: vi.fn(() => owner) });
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); vi.restoreAllMocks(); });

async function render() {
  await act(async () => root.render(<App />));
  await act(async () => Promise.resolve());
}
async function eventually(check: () => void) {
  for (let i = 0; i < 30; i++) { try { check(); return; } catch { await act(async () => new Promise(r => setTimeout(r, 0))); } }
  check();
}
function response(body: unknown, status = 200) { return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })); }

describe('production flow contracts', () => {
  it('renders the real pipeline contract for both presets', async () => {
    for (const fixture of Object.values(realOutputs)) {
      const content = fixture as any;
      const reviewed = run('awaiting_review', { content });
      vi.stubGlobal('fetch', vi.fn((url: string) => {
        if (url.endsWith('/presets')) return response([]);
        if (url.endsWith('/runs')) return response([reviewed]);
        return response(reviewed);
      }));
      await render();
      await act(async () => (container.querySelector('button.run') as HTMLButtonElement).click());
      await eventually(() => {
        expect(container.textContent).toContain(content.production.scenes[0].asset_key);
        expect(container.textContent).toContain(String(content.qa.score));
        for (const check of content.qa.check_results) expect(container.textContent).toContain(check.label);
        expect(container.textContent).toContain(content.package.title);
        expect(container.textContent).toContain(content.package.description);
        for (const tag of content.package.tags) expect(container.textContent).toContain(`#${tag}`);
      });
      act(() => root.unmount());
      container.innerHTML = '';
      root = createRoot(container);
    }
  });
  it('creates and persists an anonymous UUID on the first API request', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string) => response(url.endsWith('/presets') ? [] : [])));
    await render();
    expect(localStorage.getItem('showrunner-anonymous-id')).toBe(owner);
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].headers['X-Anonymous-User-ID']).toBe(owner);
  });

  it('starts a run, advances it, and shows the review deck', async () => {
    const created = run('draft'); const reviewed = run('awaiting_review', { content: { hook: 'A hook' } });
    vi.stubGlobal('fetch', vi.fn((url: string, options?: RequestInit) => {
      if (url.endsWith('/presets')) return response([{ id: 'survival-thriller', name: 'Survival', niche: 'N', tone: 'T', visual_style: 'V', scene_length_seconds: 8 }]);
      if (url.includes('/runs?') && options?.method === 'POST') return response(created, 201);
      if (url.endsWith('/advance')) return response(reviewed);
      return response([]);
    }));
    await render();
    await act(async () => (container.querySelector('button.primary') as HTMLButtonElement).click());
    await eventually(() => expect(container.textContent).toContain('A hook'));
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.some(([u]) => String(u).endsWith('/advance'))).toBe(true);
  });

  it.each([
    ['approve', 'APPROVE CUT ✓', run('approved')],
    ['reject', 'REJECT WITH FEEDBACK', run('rejected', { rejection_feedback: 'Make it sharper' })],
  ])('supports %s feedback action', async (action, buttonText, result) => {
    const reviewed = run('awaiting_review', { content: { hook: 'A hook' } });
    vi.stubGlobal('fetch', vi.fn((url: string, options?: RequestInit) => {
      if (url.endsWith('/presets')) return response([]);
      if (url.endsWith('/runs')) return response([reviewed]);
      if (url.endsWith(`/${action}`)) return response(result);
      return response(reviewed);
    }));
    await render();
    await act(async () => (container.querySelector('button.run') as HTMLButtonElement).click());
    await eventually(() => expect(container.textContent).toContain('A hook'));
    if (action === 'reject') {
      await act(async () => (container.querySelector('button.secondary') as HTMLButtonElement).click());
      const textarea = container.querySelector('textarea') as HTMLTextAreaElement;
      await act(async () => {
        Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, 'Make it sharper');
        textarea.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: 'Make it sharper' }));
      });
      await act(async () => (container.querySelector('button.reject') as HTMLButtonElement).click());
    } else await act(async () => (container.querySelector('button.approve') as HTMLButtonElement).click());
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.some(([u]) => String(u).endsWith(`/${action}`))).toBe(true);
  });

  it('renders readable review panels and keeps raw data collapsed', async () => {
    const reviewed = run('awaiting_review', { content: { topic: { title: 'Readable title', hook: 'A sharp hook', score: 88, reasons: ['Clear promise'] }, script: { scenes: [{ scene_number: 1, duration_seconds: 8, visual_direction: 'Wide shot', narration: 'Open on the storm.' }] }, production: { files: [{ name: 'cut.mp4', type: 'Video', size: '4 MB' }] }, qa: { checks: [{ label: 'Rendered', passed: true }], score: 99 }, packaging: { title: 'A YouTube title', description: 'A description', tags: ['mystery'] } } });
    vi.stubGlobal('fetch', vi.fn((url: string) => url.endsWith('/presets') ? response([]) : url.endsWith('/runs') ? response([reviewed]) : response(reviewed)));
    await render();
    await act(async () => (container.querySelector('button.run') as HTMLButtonElement).click());
    await eventually(() => expect(container.textContent).toContain('Readable title'));
    expect(container.textContent).toContain('SCRIPT / SCENE TIMELINE');
    expect(container.textContent).toContain('PRODUCTION / FILES');
    expect(container.textContent).toContain('PACKAGING / YOUTUBE PREVIEW');
    expect(container.querySelector('details')).toBeTruthy();
  });

  it('shows mock asset placeholders with scene associations and typed QA reasons', async () => {
    const reviewed = run('awaiting_review', { run_mode: 'mock', content: { production: { scenes: [
      { scene_number: 2, asset_key: 'scene-02', asset_type: 'audio', narration: 'Voice' },
      { scene_number: 3, asset_key: 'scene-03', asset_type: 'video', narration: 'Cut' },
    ] }, qa: { passed: false, score: 50, check_results: [
      { label: 'audio exists', passed: true, reason: 'Audio placeholder available' },
      { label: 'video render', passed: false, reason: 'Video render warning' },
    ] } } });
    vi.stubGlobal('fetch', vi.fn((url: string) => url.endsWith('/presets') ? response([]) : url.endsWith('/runs') ? response([reviewed]) : response(reviewed)));
    await render();
    await act(async () => (container.querySelector('button.run') as HTMLButtonElement).click());
    await eventually(() => expect(container.textContent).toContain('MOCK PLACEHOLDER'));
    expect(container.textContent).toContain('Scene 2');
    expect(container.textContent).toContain('audio placeholder');
    expect(container.textContent).toContain('video placeholder');
    expect(container.textContent).toContain('Video render warning');
    expect(container.textContent).toContain('QA needs review');
    expect(container.querySelector('button.approve')).toBeTruthy();
    expect(container.querySelector('button.reject')).toBeTruthy();
  });

  it('opens the in-memory demo from the first preset', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string) => url.endsWith('/presets') ? response([{ id: 'survival-thriller', name: 'Survival', niche: 'N', tone: 'T', visual_style: 'V', scene_length_seconds: 8 }]) : response([])));
    await render();
    await act(async () => (container.querySelector('button.demo-button') as HTMLButtonElement).click());
    expect(container.textContent).toContain('DEMO MODE');
    expect(container.textContent).toContain('The signal that should not exist');
    expect(container.textContent).toContain('Nothing is saved');
  });

  it('surfaces API errors to the user', async () => {
    vi.stubGlobal('fetch', vi.fn(() => response({ detail: 'service unavailable' }, 503)));
    await render();
    await eventually(() => expect(container.textContent).toContain('service unavailable'));
  });
});

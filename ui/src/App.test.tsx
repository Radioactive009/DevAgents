import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({ runs: [] }),
      })
    ));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders dashboard with primary CTA', () => {
    render(<App />);
    expect(screen.getByText('DEVAGENTS')).toBeDefined();
    expect(screen.getByText('Multi-Agent Software Engineering System')).toBeDefined();
    expect(screen.getByText('Create DevAgents Run')).toBeDefined();
  });
});

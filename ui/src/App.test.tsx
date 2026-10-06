import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders dashboard with primary CTA', () => {
    render(<App />);
    expect(screen.getByText('DEVAGENTS')).toBeDefined();
    expect(screen.getByText('Multi-Agent Software Engineering System')).toBeDefined();
    expect(screen.getByText('Create DevAgents Run')).toBeDefined();
  });
});

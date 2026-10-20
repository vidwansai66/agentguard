import { describe, it, expect } from 'vitest';
import { resolveInitialTheme, applyThemeToElement } from './ThemeContext';

describe('Theme Management Utilities', () => {
  it('defaults to dark mode when no saved theme exists', () => {
    expect(resolveInitialTheme(null)).toBe('dark');
    expect(resolveInitialTheme(undefined)).toBe('dark');
    expect(resolveInitialTheme('')).toBe('dark');
    expect(resolveInitialTheme('invalid_theme')).toBe('dark');
  });

  it('honors saved theme when valid', () => {
    expect(resolveInitialTheme('dark')).toBe('dark');
    expect(resolveInitialTheme('light')).toBe('light');
  });

  it('correctly toggles dark and light classes on root element', () => {
    const classes = new Set<string>();
    const mockEl = {
      classList: {
        add: (cls: string) => classes.add(cls),
        remove: (cls: string) => classes.delete(cls),
      },
    };

    applyThemeToElement('dark', mockEl);
    expect(classes.has('dark')).toBe(true);
    expect(classes.has('light')).toBe(false);

    applyThemeToElement('light', mockEl);
    expect(classes.has('light')).toBe(true);
    expect(classes.has('dark')).toBe(false);
  });
});

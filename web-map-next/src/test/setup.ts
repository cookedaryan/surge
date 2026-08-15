import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// jsdom implements neither of these, and Radix primitives (Select, Slider) call them on mount.
// Without the stubs any component containing one throws before a single assertion runs.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;

class StubDOMRect {
  top = 0;
  right = 0;
  bottom = 0;
  left = 0;
  constructor(
    public x = 0,
    public y = 0,
    public width = 0,
    public height = 0
  ) {}
  toJSON() {
    return this;
  }
  static fromRect(init?: { x?: number; y?: number; width?: number; height?: number }) {
    return new StubDOMRect(init?.x, init?.y, init?.width, init?.height);
  }
}
globalThis.DOMRect ??= StubDOMRect as unknown as typeof DOMRect;

if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false
  })) as unknown as typeof window.matchMedia;
}

Element.prototype.scrollIntoView ??= () => {};
Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.setPointerCapture ??= () => {};
Element.prototype.releasePointerCapture ??= () => {};

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});

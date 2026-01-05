import '@testing-library/jest-dom/vitest';

// jsdom doesn't implement matchMedia; Chakra's useMediaQuery relies on it.
if (typeof window !== 'undefined' && !(window as any).matchMedia) {
  (window as any).matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}





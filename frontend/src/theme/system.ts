import { createSystem, defaultConfig, defineConfig, defineRecipe } from "@chakra-ui/react";

// Snowball-ish + Apple-ish: subtle radii, crisp focus, quiet surfaces.
const buttonRecipe = defineRecipe({
  base: {
    borderRadius: "lg",
    fontWeight: "semibold",
    letterSpacing: "-0.01em",
    _focusVisible: {
      boxShadow: "0 0 0 4px var(--chakra-colors-focusRing)",
    },
    _disabled: {
      opacity: 0.6,
      cursor: "not-allowed",
    },
  },
});

const inputRecipe = defineRecipe({
  base: {
    borderRadius: "lg",
    bg: "bg.input",
    borderColor: "border.subtle",
    _placeholder: { color: "fg.subtle" },
    _focusVisible: {
      borderColor: "brand.500",
      boxShadow: "0 0 0 4px var(--chakra-colors-focusRing)",
    },
  },
});

export const system = createSystem(
  defaultConfig,
  defineConfig({
    globalCss: {
      "html, body, #root": {
        height: "100%",
        backgroundColor: "bg.canvas",
        color: "fg.default",
      },
      body: {
      },
    },
    theme: {
      tokens: {
        colors: {
          brand: {
            50: { value: "#E6F1FF" },
            100: { value: "#C2DBFF" },
            200: { value: "#9AC4FF" },
            300: { value: "#73AAFF" },
            400: { value: "#4F91FF" },
            500: { value: "#2A79F0" },
            600: { value: "#1B5DC3" },
            700: { value: "#124397" },
            800: { value: "#0A2B6A" },
            900: { value: "#041840" },
          },
          // Used for focus ring in recipes.
          focusRing: { value: "rgba(42,121,240,0.22)" },
        },
        fonts: {
          heading: {
            value:
              "'Space Grotesk', 'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial",
          },
          body: {
            value: "'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial",
          },
        },
        radii: {
          lg: { value: "12px" },
          xl: { value: "16px" },
        },
      },
      semanticTokens: {
        colors: {
          "bg.canvas": {
            value: {
              _light: "#F6F7FB",
              _dark: "#070B12",
            },
          },
          // Slightly elevated surface behind cards/tables.
          "bg.panel": {
            value: {
              _light: "white",
              _dark: "#0B1220",
            },
          },
          "bg.card": {
            value: {
              _light: "white",
              _dark: "rgba(17, 24, 39, 0.72)",
            },
          },
          // Subtle interactive surfaces (hover/selected states).
          "bg.muted": {
            value: {
              _light: "rgba(15, 23, 42, 0.05)",
              _dark: "rgba(255, 255, 255, 0.06)",
            },
          },
          "bg.subtle": {
            value: {
              _light: "rgba(15, 23, 42, 0.08)",
              _dark: "rgba(255, 255, 255, 0.10)",
            },
          },
          // Layout surfaces (header/sidebar) so app chrome theme stays coherent.
          "bg.header": {
            value: {
              _light: "white",
              _dark: "#0B1220",
            },
          },
          "bg.sidebar": {
            value: {
              _light: "white",
              _dark: "#0B1220",
            },
          },
          "bg.input": {
            value: {
              _light: "rgba(0,0,0,0.03)",
              _dark: "rgba(0,0,0,0.25)",
            },
          },
          "fg.default": {
            value: {
              _light: "#0B1220",
              _dark: "rgba(255,255,255,0.92)",
            },
          },
          "fg.muted": {
            value: {
              _light: "rgba(11,18,32,0.68)",
              _dark: "rgba(255,255,255,0.70)",
            },
          },
          "fg.subtle": {
            value: {
              _light: "rgba(11,18,32,0.46)",
              _dark: "rgba(255,255,255,0.55)",
            },
          },
          "border.subtle": {
            value: {
              _light: "rgba(15,23,42,0.10)",
              _dark: "rgba(255,255,255,0.12)",
            },
          },
          "border.strong": {
            value: {
              _light: "rgba(15,23,42,0.18)",
              _dark: "rgba(255,255,255,0.18)",
            },
          },
        },
      },
      recipes: {
        button: buttonRecipe,
        input: inputRecipe,
      },
    },
  })
);



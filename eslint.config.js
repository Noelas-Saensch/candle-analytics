import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        fetch: "readonly",
        location: "readonly",
        WebSocket: "readonly",
        setTimeout: "readonly",
        setInterval: "readonly",
        clearTimeout: "readonly",
        clearInterval: "readonly",
        LightweightCharts: "readonly",
        Chart: "readonly",
        HTMLSelectElement: "readonly",
        HTMLInputElement: "readonly",
        HTMLCanvasElement: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-undef": "error",
      "prefer-const": "error",
      "no-var": "error",
      "eqeqeq": ["warn", "smart"],
      "no-useless-assignment": "off",
    },
  },
];

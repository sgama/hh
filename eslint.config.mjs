// ESLint flat config for custom JS added to this site (assets/js/** or scripts/**).
// The Blowfish theme's own bundled JS is upstream and not linted here.
export default [
  {
    files: ["**/*.{js,mjs,cjs}"],
    ignores: [".tools/**", "public/**", ".hugo-dev/**", "node_modules/**"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        localStorage: "readonly",
        fetch: "readonly",
        console: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["error", { caughtErrors: "all" }],
      "no-undef": "error",
      eqeqeq: "error",
      "prefer-const": "error",
    },
  },
];

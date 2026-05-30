import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(js.configs.recommended, ...tseslint.configs.recommended, {
  languageOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    globals: {
      browser: true,
    },
  },
  rules: {
    "no-unused-vars": "warn",
    "no-console": "off",
    // Bypasses an edge case where standard rules conflict with TS compiler properties
    "@typescript-eslint/no-unused-vars": ["warn"],
  },
});

// ESLint flat config. Rules are intentionally minimal — formatting is
// handled by Prettier, so we only enforce correctness/anti-patterns:
// `@typescript-eslint/recommended` for the TS basics, `eslint-plugin-lit`
// for Lit-specific footguns (template-binding errors, attribute typos,
// etc.). Test files relax `no-explicit-any` since the @ts-expect-error
// pattern that backs setState already accepts looser typing there.

import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import lit from 'eslint-plugin-lit';

export default [
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  js.configs.recommended,
  {
    // rollup.config.js uses `process.env.BUILD` (a Node.js global). Declare it
    // so the ESLint `no-undef` rule (from js.configs.recommended) doesn't flag it.
    files: ['rollup.config.js'],
    languageOptions: {
      globals: { process: 'readonly' },
    },
  },
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.ts'],
    plugins: { lit },
    rules: {
      ...lit.configs.recommended.rules,
      // Allow leading-underscore "discard" locals — used in destructured
      // omits like `const { [field]: _, ...rest } = obj;`.
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
        },
      ],
    },
  },
  {
    // Tests use private-state injection via `as Partial<T>` and Chai's
    // BDD assertions (`expect(x).to.exist`) — both clash with rules that
    // would be appropriate for production code. Relax accordingly.
    files: ['src/__tests__/**/*.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      // Chai BDD `expect(...).to.exist` looks like an unused expression
      // but is a property accessor with side effects.
      '@typescript-eslint/no-unused-expressions': 'off',
    },
  },
];

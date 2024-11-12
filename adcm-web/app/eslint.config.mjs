import { fixupConfigRules, fixupPluginRules } from '@eslint/compat';
import react from 'eslint-plugin-react';
import prettier from 'eslint-plugin-prettier';
import typescriptEslint from '@typescript-eslint/eslint-plugin';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import spellcheck from 'eslint-plugin-spellcheck';
import tsParser from '@typescript-eslint/parser';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import js from '@eslint/js';
import { FlatCompat } from '@eslint/eslintrc';
import eslintPluginImportX from 'eslint-plugin-import-x';
import { skipWords } from './eslint-spellcheck.config.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all,
});

export default [
  {
    ignores: ['.yarn', 'dist', '.storybook', '*.js', '*.mjs', '*.cjs'],
  },
  ...fixupConfigRules(
    compat.extends(
      'eslint:recommended',
      'plugin:@typescript-eslint/recommended',
      'plugin:react-hooks/recommended',
      'plugin:storybook/recommended',
      'plugin:prettier/recommended',
      'plugin:import-x/errors',
      'plugin:import-x/warnings',
      'plugin:import-x/typescript',
      'prettier',
    ),
  ),
  {
    plugins: {
      react,
      prettier: fixupPluginRules(prettier),
      '@typescript-eslint': fixupPluginRules(typescriptEslint),
      'react-hooks': fixupPluginRules(reactHooks),
      'react-refresh': reactRefresh,
      'import-x': fixupPluginRules(eslintPluginImportX),
      spellcheck,
    },

    languageOptions: {
      parser: tsParser,
      ecmaVersion: 'latest',
      sourceType: 'module',
    },

    settings: {
      'import-x/resolver': {
        alias: {
          map: [
            ['@uikit', './src/components/uikit/'],
            ['@models', './src/models/'],
            ['@utils', './src/utils/'],
            ['@store', './src/store/'],
            ['@constants', './src/constants'],
            ['@api', './src/api/'],
          ],

          extensions: ['tsx', '.ts', '.json', '.js', '.jsx'],
        },
      },
    },
    rules: {
      'import-x/no-rename-default': 'off',
      'import-x/no-named-as-default-member': 'off',
      'import-x/no-named-as-default': 'off',
      'import-x/no-cycle': [
        'error',
        {
          maxDepth: 10,
          ignoreExternal: true,
        },
      ],
      '@typescript-eslint/no-unused-expressions': 'off',
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'react-redux',
              importNames: ['useSelector', 'useDispatch'],
              message: "Use typed `useStore` and `useDispatch` from '@hooks' instead.",
            },
            {
              name: '@reduxjs/toolkit',
              importNames: ['createAsyncThunk'],
              message: "Use typed `createAsyncThunk` from '@store/redux' instead.",
            },
          ],
        },
      ],
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          ignoreRestSiblings: true,
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],

      'react-refresh/only-export-components': 'warn',
      'object-curly-spacing': [2, 'always'],
      quotes: ['error', 'single'],
      semi: ['warn', 'always'],
      'comma-dangle': ['error', 'always-multiline'],

      'space-before-function-paren': [
        'error',
        {
          anonymous: 'always',
          named: 'never',
          asyncArrow: 'always',
        },
      ],

      'react/jsx-max-props-per-line': [
        1,
        {
          when: 'multiline',
        },
      ],
      'spellcheck/spell-checker': ['warn', { skipWords }],
      'no-console': [
        'error',
        {
          allow: ['info', 'warn', 'error'],
        },
      ],
    },
  },
];

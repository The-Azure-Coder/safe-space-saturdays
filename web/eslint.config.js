import { tanstackConfig } from '@tanstack/eslint-config'

export default [
  {
    ignores: [
      '.output/**',
      '.tanstack/**',
      'eslint.config.js',
      'prettier.config.js',
      'src/routeTree.gen.ts',
    ],
  },
  ...tanstackConfig,
  {
    rules: {
      'import/no-cycle': 'off',
      'import/order': 'off',
      'sort-imports': 'off',
    },
  },
]

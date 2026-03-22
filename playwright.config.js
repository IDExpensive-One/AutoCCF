// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/test_ui',
  testMatch: '*.js',
  timeout: 30000,
  retries: 0,
  reporter: 'list',
});

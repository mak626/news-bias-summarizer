import { defineConfig } from 'wxt';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'Nonpartisan',
    description: 'See all the different perspectives of what you are about to read.',
    action: {},
    permissions: ['tabs', 'scripting', 'activeTab'],
  },
});

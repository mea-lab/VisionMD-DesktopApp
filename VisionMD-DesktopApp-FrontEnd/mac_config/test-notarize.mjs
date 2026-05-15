// mac_config/test-notarize.mjs
import 'dotenv/config';
import notarize from './notarize.js';

const context = {
  electronPlatformName: 'darwin',
  appOutDir: 'dist/mac-arm64',
  packager: {
    appInfo: {
      productFilename: 'VisionMD',
    },
  },
};

notarize(context).catch((err) => {
  console.error('Notarize failed:', err);
  process.exitCode = 1;
});

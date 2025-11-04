import { notarize } from '@electron/notarize';
import 'dotenv/config';

export default async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;

  if (electronPlatformName !== 'darwin') return;
  if (!process.env.APPLE_ID) {
    console.log("process.env.APPLE_ID does not exist")
    return
  };
  if (!process.env.APPLE_APP_SPECIFIC_PASSWORD) {
    console.log("process.env.APPLE_ID does not exist")
    return
  };
  if (!process.env.APPLE_TEAM_ID) {
    console.log("process.env.APPLE_ID does not exist")
    return
  }

  const appName = context.packager.appInfo.productFilename;
  
  console.log('App Path submitted:', `${appOutDir}/${appName}.app`);
  console.log('Starting notarization for', appName);
  console.log('AppleID:', process.env.APPLE_ID)
  console.log('Password:', process.env.APPLE_APP_SPECIFIC_PASSWORD)
  console.log('Team ID:', process.env.APPLE_TEAM_ID)

  await notarize({
    appBundleId: 'com.mealab.visionmd',
    appPath: `${appOutDir}/${appName}.app`,
    appleId: process.env.APPLE_ID,
    appleIdPassword: process.env.APPLE_APP_SPECIFIC_PASSWORD,
    teamId: process.env.APPLE_TEAM_ID,
  });

  console.log('Notarization complete!');
}


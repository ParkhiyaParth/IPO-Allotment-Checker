import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { reportDiagnostic } from '../api/diagnostics';
import { registerPushToken } from '../api/push';

const ANDROID_CHANNEL_ID = 'ipo-alerts';

// Foreground notifications still show a banner/sound — without this handler
// they'd otherwise be silently swallowed while the app is open.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

// TEMPORARY: reportDiagnostic() calls below are for tracking down why no
// device was registering a push token in production (nothing was reaching
// the server at all, so the failure had to be silent/client-side). Safe to
// strip once that's confirmed fixed.
export async function registerForPushNotifications(): Promise<void> {
  try {
    if (!Device.isDevice) {
      await reportDiagnostic('push: not a physical device, skipping');
      return;
    }

    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
        name: 'IPO allotment alerts',
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 250, 250, 250],
      });
    }

    const existing = await Notifications.getPermissionsAsync();
    let finalStatus = existing.status;
    if (finalStatus !== 'granted') {
      const requested = await Notifications.requestPermissionsAsync();
      finalStatus = requested.status;
    }
    await reportDiagnostic(`push: permission status = ${finalStatus}`);
    if (finalStatus !== 'granted') {
      return;
    }

    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    await reportDiagnostic(`push: projectId = ${projectId ?? 'MISSING'}`);
    if (!projectId) {
      return;
    }

    const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });
    await reportDiagnostic(`push: got token, length=${token?.length ?? 0}`);

    await registerPushToken(token);
    await reportDiagnostic('push: registerPushToken succeeded');
  } catch (error) {
    await reportDiagnostic(`push: FAILED - ${String(error)}`);
  }
}

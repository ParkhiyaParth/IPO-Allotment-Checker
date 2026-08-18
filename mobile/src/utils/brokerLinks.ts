import { Linking, Platform } from 'react-native';

export type Broker = 'angel_one' | 'groww';

const BROKER_LABELS: Record<Broker, string> = {
  angel_one: 'Angel One',
  groww: 'Groww',
};

export function brokerLabel(broker: Broker): string {
  return BROKER_LABELS[broker];
}

// We deliberately don't hardcode a specific app deep-link scheme or app-store
// id here -- those aren't publicly documented/stable enough to guess, and a
// wrong guess silently opens nothing. A store search is verifiable, always
// resolves to the real app, and Play Store treats an installed app's listing
// as an "Open" button rather than "Install", so this is still effectively
// one tap for anyone who already has the broker's app.
export async function openBrokerApp(broker: Broker): Promise<void> {
  const term = encodeURIComponent(BROKER_LABELS[broker]);
  const url =
    Platform.OS === 'ios'
      ? `https://apps.apple.com/us/search?term=${term}`
      : `https://play.google.com/store/search?q=${term}&c=apps`;
  await Linking.openURL(url);
}

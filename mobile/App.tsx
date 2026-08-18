import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import * as Updates from 'expo-updates';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { reportDiagnostic } from './src/api/diagnostics';
import { RootNavigator } from './src/navigation/RootNavigator';
import { registerForPushNotifications } from './src/notifications/pushNotifications';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
    },
  },
});

export default function App() {
  useEffect(() => {
    // TEMPORARY: isolates whether this useEffect runs at all, and whether
    // the app is on an OTA update vs the originally-embedded build — safe
    // to strip once push registration is confirmed working.
    reportDiagnostic(
      `app started: embedded=${Updates.isEmbeddedLaunch}, updateId=${Updates.updateId ?? 'none'}, channel=${Updates.channel ?? 'none'}`
    ).catch(() => {});
    registerForPushNotifications();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <RootNavigator />
        <StatusBar style="dark" />
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}

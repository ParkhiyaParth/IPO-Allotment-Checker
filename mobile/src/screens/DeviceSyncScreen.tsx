import { Alert, StyleSheet, Switch, Text, View } from 'react-native';
import { useDevicePanSync } from '../hooks/useDevicePanSync';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import { ApiError } from '../api/client';

const DISCLAIMER =
  'Turning this on sends your saved PANs to the server, encrypted at rest and scoped to this device only ' +
  "(not an account). It's used only to auto-check allotment the moment it's published and push you the " +
  'result — you can turn it off and delete everything anytime.';

export function DeviceSyncScreen() {
  const { isOptedIn, isLoading, enableSync, disableSync } = useDevicePanSync();

  const handleToggle = (next: boolean) => {
    if (!next) {
      Alert.alert('Turn off auto-check?', 'This deletes your PANs from the server immediately.', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Turn Off', style: 'destructive', onPress: () => disableSync() },
      ]);
      return;
    }

    Alert.alert('Enable Zero-Tap Allotment Check?', DISCLAIMER, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Enable',
        onPress: async () => {
          try {
            await enableSync();
          } catch (err) {
            const message =
              err instanceof ApiError && err.status === 503
                ? "This server hasn't turned on PAN storage yet — try again later."
                : 'Could not enable sync. Check your connection and try again.';
            Alert.alert('Something went wrong', message);
          }
        },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <View style={styles.row}>
          <View style={styles.textColumn}>
            <Text style={styles.title}>Zero-Tap Allotment Check</Text>
            <Text style={styles.subtitle}>
              {isOptedIn
                ? 'On — your PANs are synced and will be auto-checked the moment allotment is out.'
                : 'Off — check allotment manually from the Allotment tab.'}
            </Text>
          </View>
          <Switch value={isOptedIn} onValueChange={handleToggle} disabled={isLoading} />
        </View>
      </View>
      <Text style={styles.footnote}>{DISCLAIMER}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md },
  textColumn: { flex: 1 },
  title: { fontSize: 15, fontWeight: '700', color: colors.textPrimary },
  subtitle: { fontSize: 12, color: colors.textSecondary, marginTop: spacing.xs },
  footnote: { fontSize: 12, color: colors.textSecondary, marginTop: spacing.lg, lineHeight: 18 },
});

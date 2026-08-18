import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { ResultRow } from '../components/ResultRow';
import { useCheckAllotment } from '../hooks/useCheckAllotment';
import { usePanProfiles } from '../hooks/usePanProfiles';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { AllotmentResultItem } from '../types/api';

type Props = NativeStackScreenProps<IPOsStackParamList, 'AllotmentCheck'>;

const REVEAL_DELAY_MS = 350;

export function AllotmentCheckScreen({ route }: Props) {
  const { ipoId, companyName } = route.params;
  const { profiles, isLoading: profilesLoading } = usePanProfiles();
  const { mutate, data, isError, error } = useCheckAllotment();
  const [revealedCount, setRevealedCount] = useState(0);

  useEffect(() => {
    if (!profilesLoading && profiles.length > 0) {
      setRevealedCount(0);
      mutate({ ipoId, companyName, applicants: profiles });
    }
    // Re-run only when the set of saved PANs or the IPO changes, not on every mutate identity change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ipoId, profilesLoading, profiles.length]);

  useEffect(() => {
    if (!data) return;
    if (revealedCount >= data.results.length) return;
    const timer = setTimeout(() => setRevealedCount((c) => c + 1), REVEAL_DELAY_MS);
    return () => clearTimeout(timer);
  }, [data, revealedCount]);

  const resultFor = (index: number): AllotmentResultItem | undefined => {
    if (!data || index >= revealedCount) return undefined;
    return data.results[index];
  };

  if (profilesLoading) return null;

  if (profiles.length === 0) {
    return (
      <EmptyState
        icon="🪪"
        title="No PANs saved yet"
        subtitle="Add a PAN under the My PANs tab to check allotment status."
      />
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{companyName}</Text>
        {isError ? (
          <Text style={styles.errorText}>{error?.message ?? 'Something went wrong.'}</Text>
        ) : (
          <Text style={styles.subtitle}>
            Checking {profiles.length} saved PAN{profiles.length > 1 ? 's' : ''}
          </Text>
        )}
      </View>

      <ScrollView contentContainerStyle={styles.listContent}>
        {profiles.map((profile, index) => (
          <ResultRow
            key={profile.id}
            label={profile.name}
            pan={profile.pan}
            result={resultFor(index)}
          />
        ))}
      </ScrollView>

      {isError ? (
        <TouchableOpacity
          style={styles.retryButton}
          onPress={() => {
            setRevealedCount(0);
            mutate({ ipoId, companyName, applicants: profiles });
          }}
        >
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  headerRow: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  subtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  errorText: {
    fontSize: 13,
    color: colors.statusNotAllotted,
    marginTop: spacing.xs,
  },
  listContent: {
    paddingBottom: spacing.xl,
  },
  retryButton: {
    margin: spacing.lg,
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  retryButtonText: {
    color: colors.textOnPrimary,
    fontWeight: '600',
    fontSize: 15,
  },
});

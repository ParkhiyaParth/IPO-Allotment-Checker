import { FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { EmptyState } from '../components/EmptyState';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useFamilyPortfolio, type FamilyPortfolioNudge } from '../hooks/useFamilyPortfolio';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';

function formatProfit(value: number): string {
  const rounded = Math.round(Math.abs(value));
  return `${value < 0 ? '-' : ''}₹${rounded.toLocaleString('en-IN')}`;
}

function NudgeRow({ nudge, onMarkApplied }: { nudge: FamilyPortfolioNudge; onMarkApplied: () => void }) {
  return (
    <View style={styles.nudgeRow}>
      <View style={styles.nudgeText}>
        <Text style={styles.nudgeTitle}>
          {nudge.panName} hasn't applied to {nudge.companyName}
        </Text>
        <Text style={styles.nudgeSubtitle}>
          🚀 Strong apply signal{nudge.closeDate ? ` · closes ${nudge.closeDate}` : ''}
        </Text>
      </View>
      <TouchableOpacity style={styles.markButton} onPress={onMarkApplied} activeOpacity={0.7}>
        <Text style={styles.markButtonText}>Mark Applied</Text>
      </TouchableOpacity>
    </View>
  );
}

export function FamilyPortfolioScreen() {
  const { actualProfit, estimatedProfit, nudges, isLoading, isError, markApplied } = useFamilyPortfolio();

  if (isLoading) return <SkeletonLoader />;
  if (isError) {
    return <EmptyState icon="📡" title="Couldn't load portfolio" subtitle="Pull the IPO list to refresh and try again." />;
  }

  const hasProfit = actualProfit !== 0 || estimatedProfit !== 0;

  return (
    <FlatList
      data={nudges}
      keyExtractor={(item) => `${item.ipoId}:${item.panId}`}
      contentContainerStyle={styles.listContent}
      ListHeaderComponent={
        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>Total profit across saved PANs</Text>
          {hasProfit ? (
            <>
              {actualProfit !== 0 ? (
                <Text style={[styles.summaryValue, { color: colors.statusAllotted }]}>
                  {formatProfit(actualProfit)} <Text style={styles.summaryBasis}>(actual)</Text>
                </Text>
              ) : null}
              {estimatedProfit !== 0 ? (
                <Text style={[styles.summaryValue, { color: colors.textSecondary }]}>
                  {formatProfit(estimatedProfit)} <Text style={styles.summaryBasis}>(estimated, GMP-based)</Text>
                </Text>
              ) : null}
            </>
          ) : (
            <Text style={styles.summaryEmpty}>No allotted PANs yet — check an IPO's allotment to see profit here.</Text>
          )}
          <Text style={styles.nudgesHeading}>Nudges</Text>
        </View>
      }
      renderItem={({ item }) => <NudgeRow nudge={item} onMarkApplied={() => markApplied(item.ipoId, item.panId)} />}
      ListEmptyComponent={
        <View style={styles.emptyNudges}>
          <Text style={styles.summaryEmpty}>No pending nudges — every saved PAN is marked applied on current strong-apply IPOs.</Text>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  listContent: { padding: spacing.lg, backgroundColor: colors.background },
  summaryCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.lg,
  },
  summaryTitle: { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  summaryValue: { fontSize: 22, fontWeight: '800', marginTop: spacing.sm },
  summaryBasis: { fontSize: 12, fontWeight: '600' },
  summaryEmpty: { fontSize: 13, color: colors.textSecondary, marginTop: spacing.sm },
  nudgesHeading: { fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginTop: spacing.lg },
  emptyNudges: { paddingTop: spacing.sm },
  nudgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.sm,
    gap: spacing.sm,
  },
  nudgeText: { flex: 1 },
  nudgeTitle: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  nudgeSubtitle: { fontSize: 12, color: colors.statusAllotted, marginTop: 2 },
  markButton: {
    backgroundColor: colors.primary,
    borderRadius: radii.sm,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
  },
  markButtonText: { color: colors.textOnPrimary, fontSize: 11, fontWeight: '700' },
});

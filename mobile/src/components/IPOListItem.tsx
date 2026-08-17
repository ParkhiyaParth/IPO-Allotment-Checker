import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import type { IPOSummary } from '../types/api';

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function IPOListItem({ ipo, onPress }: { ipo: IPOSummary; onPress: () => void }) {
  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.header}>
        <Text style={styles.name}>{ipo.company_name}</Text>
        {!ipo.automation_supported ? (
          <View style={styles.manualBadge}>
            <Text style={styles.manualBadgeText}>Manual</Text>
          </View>
        ) : null}
      </View>
      <Text style={styles.meta}>
        Allotment finalized {formatDate(ipo.allotment_date)} · {ipo.registrar}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.lg,
    marginHorizontal: spacing.lg,
    marginVertical: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textPrimary,
    flexShrink: 1,
  },
  meta: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  manualBadge: {
    backgroundColor: colors.statusCheckFailedBg,
    borderRadius: radii.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  manualBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.statusCheckFailed,
  },
});

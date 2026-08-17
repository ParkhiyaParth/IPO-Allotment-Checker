import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import type { AllotmentStatus } from '../types/api';

const STATUS_CONFIG: Record<AllotmentStatus, { label: string; fg: string; bg: string }> = {
  ALLOTTED: { label: 'Allotted', fg: colors.statusAllotted, bg: colors.statusAllottedBg },
  NOT_ALLOTTED: { label: 'Not Allotted', fg: colors.statusNotAllotted, bg: colors.statusNotAllottedBg },
  NOT_APPLIED: { label: 'Not Applied', fg: colors.statusNotApplied, bg: colors.statusNotAppliedBg },
  CHECK_FAILED: { label: 'Unable to Check', fg: colors.statusCheckFailed, bg: colors.statusCheckFailedBg },
};

export function StatusBadge({ status }: { status: AllotmentStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <View style={[styles.badge, { backgroundColor: config.bg }]}>
      <Text style={[styles.text, { color: config.fg }]}>{config.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.sm,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: 13,
    fontWeight: '600',
  },
});

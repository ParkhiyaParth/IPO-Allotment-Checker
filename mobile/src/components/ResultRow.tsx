import { memo } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import { maskPan } from '../utils/panMask';
import { StatusBadge } from './StatusBadge';
import type { AllotmentResultItem } from '../types/api';

interface ResultRowProps {
  label: string;
  pan: string;
  result?: AllotmentResultItem;
}

export const ResultRow = memo(function ResultRow({ label, pan, result }: ResultRowProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.info}>
          <Text style={styles.name}>{label}</Text>
          <Text style={styles.pan}>{maskPan(pan)}</Text>
        </View>
        {result ? (
          <Animated.View key="result" entering={FadeIn.duration(200)} exiting={FadeOut.duration(120)}>
            <StatusBadge status={result.status} />
          </Animated.View>
        ) : (
          <Animated.View key="checking" style={styles.checkingRow} exiting={FadeOut.duration(120)}>
            <ActivityIndicator size="small" color={colors.primary} />
            <Text style={styles.checkingText}>Checking…</Text>
          </Animated.View>
        )}
      </View>

      {result?.status === 'ALLOTTED' && result.shares_allotted ? (
        <Animated.Text style={styles.detail} entering={FadeIn.duration(200)}>
          {result.shares_allotted} shares allotted
        </Animated.Text>
      ) : null}
    </View>
  );
});

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
  info: {
    flexShrink: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  pan: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    letterSpacing: 0.5,
  },
  checkingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  checkingText: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  detail: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
});

import { useState } from 'react';
import { StyleSheet, Text, TouchableOpacity } from 'react-native';
import Animated, { FadeIn, FadeOut, LinearTransition } from 'react-native-reanimated';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import type { IpoPotentialLabel } from '../types/api';

const LABELS: Record<IpoPotentialLabel, string> = {
  strong_potential: '🔬 STRONG POTENTIAL',
  promising: 'PROMISING',
  uncertain: 'UNCERTAIN',
  weak: 'WEAK',
};

function palette(label: IpoPotentialLabel) {
  if (label === 'strong_potential') return { bg: colors.statusAllottedBg, fg: colors.statusAllotted };
  if (label === 'promising') return { bg: '#FBF3DD', fg: colors.accent };
  if (label === 'weak') return { bg: colors.statusNotAllottedBg, fg: colors.statusNotAllotted };
  return { bg: colors.statusNotAppliedBg, fg: colors.statusNotApplied };
}

export function PotentialBadge({
  label,
  score,
  reasons,
}: {
  label: IpoPotentialLabel | null;
  score: number | null;
  reasons: string[] | null;
}) {
  const [expanded, setExpanded] = useState(false);
  if (label == null) return null;
  const { bg, fg } = palette(label);

  return (
    <TouchableOpacity
      style={[styles.container, { backgroundColor: bg }]}
      onPress={() => setExpanded((e) => !e)}
      activeOpacity={0.8}
    >
      <Animated.View style={styles.headerRow} layout={LinearTransition.duration(200)}>
        <Animated.View style={styles.titleColumn} layout={LinearTransition.duration(200)}>
          <Text style={[styles.title, { color: fg }]}>{LABELS[label]}</Text>
          <Text style={styles.subtitle}>IPO Potential — research-based estimate</Text>
        </Animated.View>
        {score != null ? <Text style={[styles.score, { color: fg }]}>{score}</Text> : null}
      </Animated.View>

      {expanded ? (
        <Animated.View
          style={styles.reasonsBlock}
          entering={FadeIn.duration(180)}
          exiting={FadeOut.duration(120)}
          layout={LinearTransition.duration(200)}
        >
          {(reasons ?? []).map((reason, i) => (
            <Text key={i} style={styles.reasonText}>
              • {reason}
            </Text>
          ))}
          <Text style={styles.disclaimer}>
            Unofficial estimate from historical outcomes, news, and market data — not investment advice.
          </Text>
        </Animated.View>
      ) : (
        <Animated.Text
          style={styles.tapHint}
          entering={FadeIn.duration(180)}
          exiting={FadeOut.duration(120)}
          layout={LinearTransition.duration(200)}
        >
          Tap for details
        </Animated.Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: radii.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginTop: spacing.sm,
  },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  titleColumn: { flex: 1 },
  title: { fontSize: 12, fontWeight: '800', letterSpacing: 0.4 },
  subtitle: { fontSize: 10, color: colors.textSecondary, marginTop: 2 },
  score: { fontSize: 20, fontWeight: '800' },
  tapHint: { fontSize: 10, color: colors.textSecondary, marginTop: spacing.xs },
  reasonsBlock: { marginTop: spacing.sm },
  reasonText: { fontSize: 12, color: colors.textPrimary, marginTop: 2 },
  disclaimer: { fontSize: 10, color: colors.textSecondary, marginTop: spacing.sm, fontStyle: 'italic' },
});

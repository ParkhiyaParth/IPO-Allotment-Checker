import { useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { EmptyState } from '../components/EmptyState';
import { PressableScale } from '../components/PressableScale';
import { SkeletonLoader } from '../components/SkeletonLoader';
import {
  useApplicationTimeline,
  type ApplyCandidate,
  type PanTimeline,
  type PendingApplication,
} from '../hooks/useApplicationTimeline';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';

function formatDate(isoDate: string | null): string {
  if (!isoDate) return '—';
  return new Date(isoDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function formatAmount(value: number | null): string {
  if (value == null) return 'amount unknown';
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

function PendingRow({ entry, onClear }: { entry: PendingApplication; onClear: () => void }) {
  return (
    <View style={styles.pendingRow}>
      <View style={styles.pendingText}>
        <Text style={styles.pendingTitle}>
          {entry.companyName} · {entry.lots} lot{entry.lots > 1 ? 's' : ''}
        </Text>
        <Text style={styles.pendingSubtitle}>
          {formatAmount(entry.amountBlocked)} blocked — funds free ≈{' '}
          {entry.fundsFreeBy ? formatDate(entry.fundsFreeBy) : 'BoA date not yet known'}
        </Text>
      </View>
      <TouchableOpacity onPress={onClear} activeOpacity={0.7}>
        <Text style={styles.clearLink}>Clear</Text>
      </TouchableOpacity>
    </View>
  );
}

function statusPalette(status: ApplyCandidate['fundsStatus']) {
  if (status === 'ok') return { bg: colors.statusAllottedBg, fg: colors.statusAllotted };
  if (status === 'conflict') return { bg: colors.statusNotAllottedBg, fg: colors.statusNotAllotted };
  return { bg: colors.statusNotAppliedBg, fg: colors.textSecondary };
}

function statusText(candidate: ApplyCandidate): string {
  if (candidate.fundsStatus === 'ok') return '✅ Funds free in time';
  if (candidate.fundsStatus === 'conflict') {
    const from = candidate.conflictWith?.companyName;
    return `⚠️ Funds may still be tied up${from ? ` (from ${from})` : ''} until ~${formatDate(
      candidate.conflictWith?.fundsFreeBy ?? null,
    )}`;
  }
  return 'ℹ️ Can\'t confirm yet — a pending application\'s BoA date isn\'t known';
}

function CandidateRow({
  candidate,
  onApply,
}: {
  candidate: ApplyCandidate;
  onApply: (lots: number) => void;
}) {
  const [lots, setLots] = useState(1);
  const palette = statusPalette(candidate.fundsStatus);

  return (
    <View style={styles.candidateRow}>
      <Text style={styles.candidateTitle}>{candidate.companyName}</Text>
      <Text style={styles.candidateMeta}>
        Closes {formatDate(candidate.closeDate)}
        {candidate.reason ? ` · ${candidate.reason}` : ''}
      </Text>
      <View style={[styles.statusPill, { backgroundColor: palette.bg }]}>
        <Text style={[styles.statusPillText, { color: palette.fg }]}>{statusText(candidate)}</Text>
      </View>
      <View style={styles.applyRow}>
        <View style={styles.lotStepper}>
          <PressableScale style={styles.lotButton} onPress={() => setLots((l) => Math.max(1, l - 1))}>
            <Text style={styles.lotButtonText}>−</Text>
          </PressableScale>
          <Text style={styles.lotCount}>{lots} lot{lots > 1 ? 's' : ''}</Text>
          <PressableScale style={styles.lotButton} onPress={() => setLots((l) => l + 1)}>
            <Text style={styles.lotButtonText}>+</Text>
          </PressableScale>
        </View>
        <PressableScale style={styles.applyButton} onPress={() => onApply(lots)}>
          <Text style={styles.applyButtonText}>Mark Applied</Text>
        </PressableScale>
      </View>
    </View>
  );
}

function PanSection({
  timeline,
  onApply,
  onClear,
}: {
  timeline: PanTimeline;
  onApply: (candidate: ApplyCandidate, lots: number) => void;
  onClear: (ipoId: string) => void;
}) {
  return (
    <View style={styles.panCard}>
      <Text style={styles.panName}>{timeline.panName}</Text>

      {timeline.pending.length > 0 ? (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Pending applications</Text>
          {timeline.pending.map((entry) => (
            <PendingRow key={entry.ipoId} entry={entry} onClear={() => onClear(entry.ipoId)} />
          ))}
        </View>
      ) : (
        <Text style={styles.noPending}>No pending applications — funds fully free.</Text>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Worth applying, in priority order</Text>
        {timeline.candidates.length === 0 ? (
          <Text style={styles.noPending}>Nothing strong-signal open or upcoming right now.</Text>
        ) : (
          timeline.candidates.map((candidate) => (
            <CandidateRow
              key={candidate.ipoId}
              candidate={candidate}
              onApply={(lots) => onApply(candidate, lots)}
            />
          ))
        )}
      </View>
    </View>
  );
}

export function ApplicationTimelineScreen() {
  const { panTimelines, isLoading, isError, markApplied, removeApplication } = useApplicationTimeline();

  if (isLoading) return <SkeletonLoader />;
  if (isError) {
    return <EmptyState icon="📡" title="Couldn't load timeline" subtitle="Pull the IPO list to refresh and try again." />;
  }
  if (panTimelines.length === 0) {
    return <EmptyState icon="🪪" title="No PANs saved yet" subtitle="Add a PAN under My PANs to start planning." />;
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.disclaimer}>
        "Funds free" dates are an approximation (BoA date + ~1 day) based on typical UPI-mandate release timing —
        actual bank processing can vary.
      </Text>
      {panTimelines.map((timeline) => (
        <PanSection
          key={timeline.panId}
          timeline={timeline}
          onApply={(candidate, lots) => markApplied(candidate, timeline.panId, timeline.panName, lots)}
          onClear={(ipoId) => removeApplication(ipoId, timeline.panId)}
        />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, backgroundColor: colors.background },
  disclaimer: {
    fontSize: 11,
    color: colors.textSecondary,
    fontStyle: 'italic',
    marginBottom: spacing.lg,
  },
  panCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  panName: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  section: { marginTop: spacing.md },
  sectionLabel: { fontSize: 12, fontWeight: '700', color: colors.textSecondary, marginBottom: spacing.sm },
  noPending: { fontSize: 13, color: colors.textSecondary, marginTop: spacing.xs },
  pendingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.background,
    borderRadius: radii.sm,
    padding: spacing.sm,
    marginBottom: spacing.xs,
    gap: spacing.sm,
  },
  pendingText: { flex: 1 },
  pendingTitle: { fontSize: 13, fontWeight: '600', color: colors.textPrimary },
  pendingSubtitle: { fontSize: 11, color: colors.textSecondary, marginTop: 2 },
  clearLink: { fontSize: 12, color: colors.statusNotAllotted, fontWeight: '600' },
  candidateRow: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    padding: spacing.sm,
    marginBottom: spacing.sm,
  },
  candidateTitle: { fontSize: 14, fontWeight: '700', color: colors.textPrimary },
  candidateMeta: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  statusPill: {
    alignSelf: 'flex-start',
    borderRadius: radii.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    marginTop: spacing.sm,
  },
  statusPillText: { fontSize: 11, fontWeight: '700' },
  applyRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.sm,
    gap: spacing.sm,
  },
  lotStepper: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  lotButton: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  lotButtonText: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  lotCount: { fontSize: 12, color: colors.textPrimary, minWidth: 48, textAlign: 'center' },
  applyButton: {
    backgroundColor: colors.primary,
    borderRadius: radii.sm,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
  },
  applyButtonText: { color: colors.textOnPrimary, fontSize: 11, fontWeight: '700' },
});

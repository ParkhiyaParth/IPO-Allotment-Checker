import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { GmpSparkline } from '../components/GmpSparkline';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useIpoCatalogDetail } from '../hooks/useIpoCatalog';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { ApplySignal, SubscriptionCategory } from '../types/api';
import { brokerLabel, openBrokerApp } from '../utils/brokerLinks';

type Props = NativeStackScreenProps<IPOsStackParamList, 'IPODetail'>;

function fmt(value: string | number | null): string {
  return value == null ? '—' : String(value);
}

function formatProfit(value: number): string {
  const rounded = Math.round(Math.abs(value));
  return `${value < 0 ? '-' : '+'}₹${rounded.toLocaleString('en-IN')}`;
}

function formatTimes(value: number): string {
  // Cap to 4 significant figures (e.g. "5.233x", "12.35x", "123.5x")
  // instead of raw floating-point division showing many decimal places,
  // then strip any trailing zeros toPrecision introduces.
  return `${parseFloat(value.toPrecision(4))}x`;
}

const APPLY_SIGNAL_LABELS: Record<ApplySignal, string> = {
  strong_apply: '🚀 Strong Apply',
  consider: 'Consider',
  skip: 'Skip',
};

function applySignalPalette(signal: ApplySignal) {
  if (signal === 'strong_apply') return { bg: colors.statusAllottedBg, fg: colors.statusAllotted };
  if (signal === 'consider') return { bg: colors.statusCheckFailedBg, fg: colors.statusCheckFailed };
  return { bg: colors.statusNotAppliedBg, fg: colors.statusNotApplied };
}

function promptBrokerChoice(companyName: string, reason: string | null) {
  const disclaimer =
    (reason ? `${reason}. ` : '') +
    'This is an unofficial estimate from GMP and subscription data, not investment advice. ' +
    "You'll still need to apply and approve the UPI mandate yourself in your broker app.";

  Alert.alert(`Apply for ${companyName}?`, disclaimer, [
    { text: brokerLabel('angel_one'), onPress: () => openBrokerApp('angel_one') },
    { text: brokerLabel('groww'), onPress: () => openBrokerApp('groww') },
    { text: 'Cancel', style: 'cancel' },
  ]);
}

function SubscriptionRow({ label, category }: { label: string; category: SubscriptionCategory }) {
  return (
    <View style={styles.tableRow}>
      <Text style={styles.tableCell}>{label}</Text>
      <Text style={styles.tableCell}>{fmt(category.offered)}</Text>
      <Text style={styles.tableCell}>{fmt(category.applied)}</Text>
      <Text style={styles.tableCell}>{category.times != null ? formatTimes(category.times) : '—'}</Text>
    </View>
  );
}

export function IPODetailScreen({ route }: Props) {
  const { ipoId } = route.params;
  const { data, isLoading, isError } = useIpoCatalogDetail(ipoId);

  if (isLoading) return <SkeletonLoader />;
  if (isError || !data) {
    return <EmptyState icon="📡" title="Couldn't load IPO details" subtitle="Pull to refresh from the list." />;
  }

  const profitColor =
    data.profit_per_lot == null
      ? colors.textSecondary
      : data.profit_per_lot >= 0
        ? colors.statusAllotted
        : colors.statusNotAllotted;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {data.profit_per_lot != null ? (
        <View style={[styles.profitCard, { backgroundColor: data.profit_per_lot >= 0 ? colors.statusAllottedBg : colors.statusNotAllottedBg }]}>
          <Text style={[styles.profitCardLabel, { color: profitColor }]}>
            {data.profit_basis === 'actual' ? 'PROFIT PER LOT' : 'ESTIMATED PROFIT PER LOT'}
          </Text>
          <Text style={[styles.profitCardValue, { color: profitColor }]}>{formatProfit(data.profit_per_lot)}</Text>
          <Text style={styles.profitCardSubtitle}>
            {data.profit_basis === 'actual'
              ? 'Based on current market price vs. issue price'
              : 'Based on grey market premium — not guaranteed'}
          </Text>
        </View>
      ) : null}

      {data.apply_signal != null ? (
        <View style={[styles.applyCard, { backgroundColor: applySignalPalette(data.apply_signal).bg }]}>
          <View style={styles.applyCardText}>
            <Text style={[styles.applyCardLabel, { color: applySignalPalette(data.apply_signal).fg }]}>
              {APPLY_SIGNAL_LABELS[data.apply_signal]}
            </Text>
            {data.apply_signal_reason ? (
              <Text style={styles.applyCardReason}>{data.apply_signal_reason}</Text>
            ) : null}
          </View>
          {data.apply_signal === 'strong_apply' ? (
            <TouchableOpacity
              style={styles.applyNowButton}
              onPress={() => promptBrokerChoice(data.company_name, data.apply_signal_reason)}
              activeOpacity={0.7}
            >
              <Text style={styles.applyNowButtonText}>APPLY NOW</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      ) : null}

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>IPO Details</Text>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Open Date</Text>
          <Text style={styles.fieldValue}>{fmt(data.open_date)}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Close Date</Text>
          <Text style={styles.fieldValue}>{fmt(data.close_date)}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>📅 Allotment Date</Text>
          <Text style={[styles.fieldValue, styles.allotmentDateValue]}>{fmt(data.boa_date)}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Price Band</Text>
          <Text style={styles.fieldValue}>
            {data.price_band_low != null && data.price_band_high != null
              ? `₹${data.price_band_low} - ₹${data.price_band_high}`
              : '—'}
          </Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Issue Price</Text>
          <Text style={styles.fieldValue}>{data.issue_price != null ? `₹${data.issue_price}` : '—'}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Lot Size</Text>
          <Text style={styles.fieldValue}>{fmt(data.lot_size)}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Issue Size</Text>
          <Text style={styles.fieldValue}>{data.issue_size_cr != null ? `₹${data.issue_size_cr} cr` : '—'}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>GMP</Text>
          <View style={styles.gmpValueColumn}>
            <Text style={styles.fieldValue}>
              {data.gmp_value != null
                ? `${data.gmp_value}${data.gmp_percent != null ? ` (${data.gmp_percent.toFixed(0)}%)` : ''}`
                : '—'}
            </Text>
            <GmpSparkline trend={data.gmp_trend} />
          </View>
        </View>
        {data.retail_allotment_probability != null ? (
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Est. allotment odds</Text>
            <Text style={styles.fieldValue}>{Math.round(data.retail_allotment_probability * 100)}% (approx.)</Text>
          </View>
        ) : null}
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Subscription Details</Text>
        <View style={styles.tableRow}>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Category</Text>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Offered</Text>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Applied</Text>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Times</Text>
        </View>
        <SubscriptionRow label="QIB" category={data.subscription_qib} />
        <SubscriptionRow label="HNI" category={data.subscription_hni} />
        <SubscriptionRow label="Retail" category={data.subscription_retail} />
      </View>

      {data.status === 'closed' ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Listing</Text>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Listing Date</Text>
            <Text style={styles.fieldValue}>{fmt(data.listing_date)}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Listing Price</Text>
            <Text style={styles.fieldValue}>{data.listing_price != null ? `₹${data.listing_price}` : '—'}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Current Price</Text>
            <Text style={styles.fieldValue}>{data.current_price != null ? `₹${data.current_price}` : '—'}</Text>
          </View>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, backgroundColor: colors.background },
  profitCard: {
    borderRadius: 16,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    alignItems: 'center',
  },
  profitCardLabel: { fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  profitCardValue: { fontSize: 28, fontWeight: '800', marginTop: spacing.xs },
  profitCardSubtitle: { fontSize: 12, color: colors.textSecondary, marginTop: spacing.xs, textAlign: 'center' },
  applyCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderRadius: 16,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    gap: spacing.sm,
  },
  applyCardText: { flex: 1 },
  applyCardLabel: { fontSize: 14, fontWeight: '800', letterSpacing: 0.3 },
  applyCardReason: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  applyNowButton: {
    backgroundColor: colors.statusAllotted,
    borderRadius: 8,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  applyNowButtonText: { color: colors.textOnPrimary, fontSize: 12, fontWeight: '800', letterSpacing: 0.3 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.md },
  fieldRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing.xs },
  fieldLabel: { fontSize: 13, color: colors.textSecondary },
  fieldValue: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  allotmentDateValue: { color: colors.primary, fontWeight: '700' },
  gmpValueColumn: { alignItems: 'flex-end' },
  tableRow: { flexDirection: 'row', paddingVertical: spacing.xs },
  tableCell: { flex: 1, fontSize: 13, color: colors.textPrimary, textAlign: 'center' },
  tableHeaderCell: { fontWeight: '700', color: colors.textSecondary },
});

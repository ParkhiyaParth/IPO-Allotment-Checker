import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import type { IPOCatalogStatus, IPOCatalogSummary } from '../types/api';

function formatDate(isoDate: string | null): string {
  if (!isoDate) return '—';
  return new Date(isoDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function formatPriceBand(low: number | null, high: number | null): string {
  if (low == null || high == null) return '—';
  return low === high ? `₹${low}` : `₹${low} - ₹${high}`;
}

function formatGmp(value: number | null, percent: number | null): string {
  if (value == null) return '—';
  return percent != null ? `₹${value} (${percent.toFixed(0)}%)` : `₹${value}`;
}

function formatProfit(value: number): string {
  const rounded = Math.round(Math.abs(value));
  return `${value < 0 ? '-' : '+'}₹${rounded.toLocaleString('en-IN')}`;
}

const STATUS_LABELS: Record<IPOCatalogStatus, string> = {
  open: 'OPEN',
  upcoming: 'UPCOMING',
  closed: 'CLOSED',
};

function StatusPill({ status }: { status: IPOCatalogStatus }) {
  const palette =
    status === 'open'
      ? { bg: colors.statusAllottedBg, fg: colors.statusAllotted }
      : status === 'upcoming'
        ? { bg: colors.statusCheckFailedBg, fg: colors.statusCheckFailed }
        : { bg: colors.statusNotAppliedBg, fg: colors.statusNotApplied };

  return (
    <View style={[styles.statusPill, { backgroundColor: palette.bg }]}>
      <Text style={[styles.statusPillText, { color: palette.fg }]}>{STATUS_LABELS[status]}</Text>
    </View>
  );
}

function ProfitBanner({ ipo }: { ipo: IPOCatalogSummary }) {
  if (ipo.profit_per_lot == null) {
    return (
      <View style={[styles.profitBanner, styles.profitBannerNeutral]}>
        <Text style={styles.profitNeutralText}>Profit estimate not available yet</Text>
      </View>
    );
  }

  const isGain = ipo.profit_per_lot >= 0;
  const bg = isGain ? colors.statusAllottedBg : colors.statusNotAllottedBg;
  const fg = isGain ? colors.statusAllotted : colors.statusNotAllotted;

  return (
    <View style={[styles.profitBanner, { backgroundColor: bg }]}>
      <View>
        <Text style={[styles.profitLabel, { color: fg }]}>
          {ipo.profit_basis === 'actual' ? 'PROFIT PER LOT' : 'EST. PROFIT PER LOT'}
        </Text>
        <Text style={styles.profitSubLabel}>
          {ipo.profit_basis === 'actual' ? 'Based on current market price' : 'Based on grey market premium'}
        </Text>
      </View>
      <Text style={[styles.profitValue, { color: fg }]}>{formatProfit(ipo.profit_per_lot)}</Text>
    </View>
  );
}

export function IPOCard({
  ipo,
  onView,
  onCheckAllotment,
}: {
  ipo: IPOCatalogSummary;
  onView: () => void;
  onCheckAllotment?: () => void;
}) {
  const gmpColor =
    ipo.gmp_value == null
      ? colors.textSecondary
      : ipo.gmp_value >= 0
        ? colors.statusAllotted
        : colors.statusNotAllotted;

  const showPriceComparison = ipo.status === 'closed' && ipo.listing_price != null && ipo.current_price != null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.name} numberOfLines={2}>
          {ipo.company_name}
        </Text>
        <StatusPill status={ipo.status} />
      </View>
      <Text style={styles.meta}>
        {formatDate(ipo.open_date)} - {formatDate(ipo.close_date)}
      </Text>

      <ProfitBanner ipo={ipo} />

      <View style={styles.row}>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Price</Text>
          <Text style={styles.fieldValue}>{formatPriceBand(ipo.price_band_low, ipo.price_band_high)}</Text>
        </View>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Lot Size</Text>
          <Text style={styles.fieldValue}>{ipo.lot_size ?? '—'}</Text>
        </View>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Issue Size</Text>
          <Text style={styles.fieldValue}>{ipo.issue_size_cr != null ? `₹${ipo.issue_size_cr} cr` : '—'}</Text>
        </View>
      </View>

      <View style={styles.row}>
        <Text style={styles.fieldLabel}>GMP</Text>
        <Text style={[styles.gmpValue, { color: gmpColor }]}>{formatGmp(ipo.gmp_value, ipo.gmp_percent)}</Text>
      </View>

      {showPriceComparison ? (
        <View style={styles.row}>
          <View style={styles.field}>
            <Text style={styles.fieldLabel}>Listing Price</Text>
            <Text style={styles.fieldValue}>₹{ipo.listing_price}</Text>
          </View>
          <View style={styles.field}>
            <Text style={styles.fieldLabel}>Current Price</Text>
            <Text style={styles.fieldValue}>₹{ipo.current_price}</Text>
          </View>
        </View>
      ) : null}

      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.viewButton} onPress={onView} activeOpacity={0.7}>
          <Text style={styles.viewButtonText}>VIEW DETAILS</Text>
        </TouchableOpacity>
        {onCheckAllotment ? (
          <TouchableOpacity style={styles.allotmentButton} onPress={onCheckAllotment} activeOpacity={0.7}>
            <Text style={styles.allotmentButtonText}>ALLOTMENT</Text>
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.lg,
    marginHorizontal: spacing.lg,
    marginVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#0F1430',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: spacing.sm },
  name: { flex: 1, fontSize: 17, fontWeight: '700', color: colors.textPrimary, lineHeight: 22 },
  statusPill: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radii.sm,
  },
  statusPillText: { fontSize: 11, fontWeight: '700', letterSpacing: 0.4 },
  meta: { fontSize: 13, color: colors.textSecondary, marginTop: spacing.xs },
  profitBanner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderRadius: radii.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    marginTop: spacing.md,
  },
  profitBannerNeutral: { backgroundColor: colors.statusNotAppliedBg },
  profitLabel: { fontSize: 11, fontWeight: '700', letterSpacing: 0.4 },
  profitSubLabel: { fontSize: 11, color: colors.textSecondary, marginTop: 2 },
  profitNeutralText: { fontSize: 13, color: colors.textSecondary },
  profitValue: { fontSize: 20, fontWeight: '800' },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.md },
  field: { flex: 1 },
  fieldLabel: { fontSize: 12, color: colors.textSecondary },
  fieldValue: { fontSize: 14, fontWeight: '600', color: colors.textPrimary, marginTop: 2 },
  gmpValue: { fontSize: 14, fontWeight: '700' },
  buttonRow: { flexDirection: 'row', marginTop: spacing.lg, gap: spacing.sm },
  viewButton: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: radii.sm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  viewButtonText: { fontWeight: '700', color: colors.primary, fontSize: 13, letterSpacing: 0.3 },
  allotmentButton: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: radii.sm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  allotmentButtonText: { fontWeight: '700', color: colors.textOnPrimary, fontSize: 13, letterSpacing: 0.3 },
});

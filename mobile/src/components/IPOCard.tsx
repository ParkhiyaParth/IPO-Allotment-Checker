import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import type { IPOCatalogSummary } from '../types/api';

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
  return percent != null ? `${value} (${percent.toFixed(0)}%)` : `${value}`;
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
      <Text style={styles.name}>{ipo.company_name}</Text>
      <Text style={styles.meta}>
        {formatDate(ipo.open_date)} - {formatDate(ipo.close_date)}
      </Text>

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
          <Text style={styles.viewButtonText}>VIEW</Text>
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
    borderRadius: radii.md,
    padding: spacing.lg,
    marginHorizontal: spacing.lg,
    marginVertical: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  name: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  meta: { fontSize: 13, color: colors.textSecondary, marginTop: spacing.xs },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.md },
  field: { flex: 1 },
  fieldLabel: { fontSize: 12, color: colors.textSecondary },
  fieldValue: { fontSize: 14, fontWeight: '600', color: colors.textPrimary, marginTop: 2 },
  gmpValue: { fontSize: 14, fontWeight: '700' },
  buttonRow: { flexDirection: 'row', marginTop: spacing.lg, gap: spacing.sm },
  viewButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.sm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  viewButtonText: { fontWeight: '700', color: colors.textPrimary },
  allotmentButton: {
    flex: 1,
    backgroundColor: colors.statusAllotted,
    borderRadius: radii.sm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  allotmentButtonText: { fontWeight: '700', color: colors.textOnPrimary },
});

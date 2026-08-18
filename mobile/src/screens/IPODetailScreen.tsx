import { ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useIpoCatalogDetail } from '../hooks/useIpoCatalog';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { SubscriptionCategory } from '../types/api';

type Props = NativeStackScreenProps<IPOsStackParamList, 'IPODetail'>;

function fmt(value: string | number | null): string {
  return value == null ? '—' : String(value);
}

function SubscriptionRow({ label, category }: { label: string; category: SubscriptionCategory }) {
  return (
    <View style={styles.tableRow}>
      <Text style={styles.tableCell}>{label}</Text>
      <Text style={styles.tableCell}>{fmt(category.offered)}</Text>
      <Text style={styles.tableCell}>{fmt(category.applied)}</Text>
      <Text style={styles.tableCell}>{category.times != null ? `${category.times}x` : '—'}</Text>
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

  return (
    <ScrollView contentContainerStyle={styles.container}>
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
          <Text style={styles.fieldLabel}>Price Band</Text>
          <Text style={styles.fieldValue}>
            {data.price_band_low != null && data.price_band_high != null
              ? `₹${data.price_band_low} - ₹${data.price_band_high}`
              : '—'}
          </Text>
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
          <Text style={styles.fieldValue}>
            {data.gmp_value != null
              ? `${data.gmp_value}${data.gmp_percent != null ? ` (${data.gmp_percent.toFixed(0)}%)` : ''}`
              : '—'}
          </Text>
        </View>
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
  tableRow: { flexDirection: 'row', paddingVertical: spacing.xs },
  tableCell: { flex: 1, fontSize: 13, color: colors.textPrimary, textAlign: 'center' },
  tableHeaderCell: { fontWeight: '700', color: colors.textSecondary },
});

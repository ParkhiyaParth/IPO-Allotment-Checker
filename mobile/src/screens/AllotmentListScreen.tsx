import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { IPOListItem } from '../components/IPOListItem';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useApplySignalTrackRecord } from '../hooks/useIpoCatalog';
import { useRecentIpos } from '../hooks/useRecentIpos';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { AllotmentStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<AllotmentStackParamList, 'AllotmentList'>;

function TrackRecordStat() {
  const { data } = useApplySignalTrackRecord();
  if (!data || data.total === 0 || data.hit_rate == null) return null;

  return (
    <Text style={styles.trackRecord}>
      Apply-signal accuracy so far: {Math.round(data.hit_rate * 100)}% ({data.correct}/{data.total} closed IPOs)
    </Text>
  );
}

export function AllotmentListScreen({ navigation }: Props) {
  const { data, isLoading, isError, refetch, isRefetching } = useRecentIpos();

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Check Allotment</Text>
        <Text style={styles.subtitle}>Recent IPOs with allotment out · tap to check all your PANs</Text>
        <TrackRecordStat />
        <TouchableOpacity onPress={() => navigation.navigate('FamilyPortfolio')} activeOpacity={0.7}>
          <Text style={styles.portfolioLink}>View Family Portfolio →</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('ApplicationTimeline')} activeOpacity={0.7}>
          <Text style={styles.portfolioLink}>View Application Timeline →</Text>
        </TouchableOpacity>
      </View>

      {isLoading ? (
        <SkeletonLoader />
      ) : isError ? (
        <EmptyState
          icon="📡"
          title="Couldn't load IPOs"
          subtitle="Check that the backend server is running and reachable, then pull to refresh."
        />
      ) : !data || data.length === 0 ? (
        <EmptyState icon="🗂️" title="No recent IPOs yet" subtitle="Pull to refresh." />
      ) : (
        <FlatList
          data={data}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <IPOListItem
              ipo={item}
              onPress={() =>
                navigation.navigate('AllotmentCheck', { ipoId: item.id, companyName: item.company_name })
              }
            />
          )}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  headerRow: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  subtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  trackRecord: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
    marginTop: spacing.sm,
  },
  portfolioLink: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.primary,
    marginTop: spacing.sm,
  },
  listContent: {
    paddingBottom: spacing.xl,
  },
});

import { FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { IPOListItem } from '../components/IPOListItem';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useRecentIpos } from '../hooks/useRecentIpos';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<IPOsStackParamList, 'IPOList'>;

export function IPOListScreen({ navigation }: Props) {
  const { data, isLoading, isError, refetch, isRefetching } = useRecentIpos();

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Recent IPOs</Text>
        <Text style={styles.subtitle}>Allotment finalized · tap to check your PANs</Text>
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
                navigation.navigate('IPODetail', { ipoId: item.id, companyName: item.company_name })
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
  listContent: {
    paddingBottom: spacing.xl,
  },
});

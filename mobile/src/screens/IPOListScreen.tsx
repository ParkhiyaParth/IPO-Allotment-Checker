import { useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import type { GestureStateChangeEvent, PanGestureHandlerEventPayload } from 'react-native-gesture-handler';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { IPOCard } from '../components/IPOCard';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useIpoCatalog } from '../hooks/useIpoCatalog';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { IPOCatalogStatus } from '../types/api';

type Props = NativeStackScreenProps<IPOsStackParamList, 'IPOList'>;

const TABS: { key: IPOCatalogStatus; label: string }[] = [
  { key: 'open', label: 'OPEN' },
  { key: 'upcoming', label: 'UPCOMING' },
  { key: 'closed', label: 'CLOSED' },
];

// How far (px) a horizontal drag must travel before it counts as a
// deliberate "switch tabs" swipe rather than an accidental brush.
const SWIPE_THRESHOLD_PX = 60;

export function IPOListScreen({ navigation }: Props) {
  const [status, setStatus] = useState<IPOCatalogStatus>('open');
  const { data, isLoading, isError, refetch, isRefetching } = useIpoCatalog(status);

  const currentIndex = TABS.findIndex((t) => t.key === status);

  // activeOffsetX/failOffsetY let this only ever claim a predominantly
  // horizontal drag -- a vertical drag on the FlatList fails this gesture
  // immediately and falls through to the list's own native scrolling,
  // so swiping to switch tabs and scrolling the list never fight each other.
  const swipeGesture = Gesture.Pan()
    .activeOffsetX([-20, 20])
    .failOffsetY([-15, 15])
    .onEnd((event: GestureStateChangeEvent<PanGestureHandlerEventPayload>) => {
      if (event.translationX <= -SWIPE_THRESHOLD_PX && currentIndex < TABS.length - 1) {
        setStatus(TABS[currentIndex + 1].key);
      } else if (event.translationX >= SWIPE_THRESHOLD_PX && currentIndex > 0) {
        setStatus(TABS[currentIndex - 1].key);
      }
    });

  return (
    <View style={styles.container}>
      <View style={styles.tabRow}>
        {TABS.map((tab) => (
          <TouchableOpacity key={tab.key} onPress={() => setStatus(tab.key)}>
            <Text style={[styles.tabLabel, status === tab.key && styles.tabLabelActive]}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <GestureDetector gesture={swipeGesture}>
        <View style={styles.swipeArea}>
          {isLoading ? (
            <SkeletonLoader />
          ) : isError ? (
            <EmptyState
              icon="📡"
              title="Couldn't load IPOs"
              subtitle="Check that the backend server is running and reachable, then pull to refresh."
            />
          ) : !data || data.length === 0 ? (
            <EmptyState icon="🗂️" title={`No ${status} IPOs`} subtitle="Pull to refresh." />
          ) : (
            <FlatList
              data={data}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <IPOCard
                  ipo={item}
                  onView={() => navigation.navigate('IPODetail', { ipoId: item.id, companyName: item.company_name })}
                  onCheckAllotment={
                    item.linked_registrar_ipo_id
                      ? () =>
                          navigation.navigate('AllotmentCheck', {
                            ipoId: item.linked_registrar_ipo_id as string,
                            companyName: item.company_name,
                          })
                      : undefined
                  }
                />
              )}
              contentContainerStyle={styles.listContent}
              refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
            />
          )}
        </View>
      </GestureDetector>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  tabRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
    gap: spacing.lg,
  },
  tabLabel: { fontSize: 14, fontWeight: '700', color: colors.textSecondary, paddingBottom: spacing.xs },
  tabLabelActive: { color: colors.primary, borderBottomWidth: 2, borderBottomColor: colors.primary },
  swipeArea: { flex: 1 },
  listContent: { paddingBottom: spacing.xl },
});

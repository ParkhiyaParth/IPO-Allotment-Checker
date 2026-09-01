import { useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View, useWindowDimensions } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import type {
  GestureStateChangeEvent,
  GestureUpdateEvent,
  PanGestureHandlerEventPayload,
} from 'react-native-gesture-handler';
import Animated, { Easing, runOnJS, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { UseQueryResult } from '@tanstack/react-query';
import { EmptyState } from '../components/EmptyState';
import { IPOCard } from '../components/IPOCard';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useIpoCatalog } from '../hooks/useIpoCatalog';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { IPOCatalogStatus, IPOCatalogSummary } from '../types/api';

type Props = NativeStackScreenProps<IPOsStackParamList, 'IPOList'>;

const TABS: { key: IPOCatalogStatus; label: string }[] = [
  { key: 'open', label: 'OPEN' },
  { key: 'upcoming', label: 'UPCOMING' },
  { key: 'closed', label: 'CLOSED' },
];

// Fraction of screen width a drag must cover to commit a page change, OR a
// fast-enough flick regardless of distance -- mirrors how WhatsApp's own
// Chats/Status/Calls pager decides between settling on the new page and
// snapping back, so the current and next pages (laid out side by side)
// are both visibly dragged together the whole time, not just a small
// drag-hint applied to a single page.
const SWIPE_COMMIT_RATIO = 0.35;
const FLICK_VELOCITY_PX_S = 800;
const SETTLE_DURATION_MS = 260;
const EASE_OUT = Easing.out(Easing.cubic);

function TabPage({
  status,
  query,
  width,
  navigation,
}: {
  status: IPOCatalogStatus;
  query: UseQueryResult<IPOCatalogSummary[]>;
  width: number;
  navigation: Props['navigation'];
}) {
  const { data, isLoading, isError, refetch, isRefetching } = query;

  return (
    <View style={[styles.page, { width }]}>
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
  );
}

export function IPOListScreen({ navigation }: Props) {
  const { width } = useWindowDimensions();
  const [status, setStatus] = useState<IPOCatalogStatus>('open');

  // Fetch all three tabs up front (each is its own react-query cache entry,
  // so these run in parallel) instead of only the active one -- lets the
  // pager below hold real, already-loaded content for every page, not just
  // the active one.
  const openQuery = useIpoCatalog('open');
  const upcomingQuery = useIpoCatalog('upcoming');
  const closedQuery = useIpoCatalog('closed');

  const activeIndex = TABS.findIndex((t) => t.key === status);

  // translateX always mirrors the pager strip's real on-screen position: at
  // rest it's exactly -activeIndex * width; mid-drag it also carries the
  // live finger offset. Because all three pages sit side by side in one
  // 3*width-wide row, this single value dragging that whole row is what
  // makes the current page and the adjacent one both visibly slide
  // together -- not a single page rubber-banding on its own.
  const translateX = useSharedValue(-activeIndex * width);
  const isAnimating = useSharedValue(false);

  const pagerStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
  }));

  const settleTo = (targetIndex: number) => {
    isAnimating.value = true;
    translateX.value = withTiming(-targetIndex * width, { duration: SETTLE_DURATION_MS, easing: EASE_OUT }, () => {
      'worklet';
      isAnimating.value = false;
    });
    if (targetIndex !== activeIndex) {
      setStatus(TABS[targetIndex].key);
    }
  };

  const changeTab = (targetIndex: number) => {
    if (targetIndex === activeIndex || isAnimating.value) return;
    settleTo(targetIndex);
  };

  // activeOffsetX/failOffsetY let this only ever claim a predominantly
  // horizontal drag -- a vertical drag on the FlatList fails this gesture
  // immediately and falls through to the list's own native scrolling, so
  // swiping to switch tabs and scrolling the list never fight each other.
  // onUpdate runs entirely as a UI-thread worklet (no runOnJS) so the drag
  // stays responsive even while the JS thread is busy with a refetch or a
  // FlatList render; onEnd only crosses to JS once, to settle on whichever
  // page (new or the same one) the drag actually resolved to.
  const swipeGesture = Gesture.Pan()
    .activeOffsetX([-20, 20])
    .failOffsetY([-15, 15])
    .onUpdate((event: GestureUpdateEvent<PanGestureHandlerEventPayload>) => {
      'worklet';
      if (isAnimating.value) return;
      // Resistance at the ends (no earlier/later tab to reveal) so
      // dragging past the first/last tab feels like hitting a soft wall
      // instead of sliding away into nothing.
      const atStart = activeIndex === 0 && event.translationX > 0;
      const atEnd = activeIndex === TABS.length - 1 && event.translationX < 0;
      const resistance = atStart || atEnd ? 0.35 : 1;
      translateX.value = -activeIndex * width + event.translationX * resistance;
    })
    .onEnd((event: GestureStateChangeEvent<PanGestureHandlerEventPayload>) => {
      'worklet';
      if (isAnimating.value) return;
      const distance = event.translationX;
      const committed = Math.abs(distance) > width * SWIPE_COMMIT_RATIO || Math.abs(event.velocityX) > FLICK_VELOCITY_PX_S;
      let targetIndex = activeIndex;
      if (committed) {
        if (distance < 0 && activeIndex < TABS.length - 1) targetIndex = activeIndex + 1;
        else if (distance > 0 && activeIndex > 0) targetIndex = activeIndex - 1;
      }
      runOnJS(settleTo)(targetIndex);
    });

  return (
    <View style={styles.container}>
      <View style={styles.tabRow}>
        {TABS.map((tab, index) => (
          <TouchableOpacity key={tab.key} onPress={() => changeTab(index)}>
            <Text style={[styles.tabLabel, status === tab.key && styles.tabLabelActive]}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <GestureDetector gesture={swipeGesture}>
        <View style={styles.swipeArea}>
          <Animated.View style={[styles.pagerRow, { width: width * TABS.length }, pagerStyle]}>
            <TabPage status="open" query={openQuery} width={width} navigation={navigation} />
            <TabPage status="upcoming" query={upcomingQuery} width={width} navigation={navigation} />
            <TabPage status="closed" query={closedQuery} width={width} navigation={navigation} />
          </Animated.View>
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
  swipeArea: { flex: 1, overflow: 'hidden' },
  pagerRow: { flex: 1, flexDirection: 'row' },
  page: { flex: 1 },
  listContent: { paddingBottom: spacing.xl },
});

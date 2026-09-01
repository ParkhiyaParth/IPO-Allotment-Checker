import { useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import type {
  GestureStateChangeEvent,
  GestureUpdateEvent,
  PanGestureHandlerEventPayload,
} from 'react-native-gesture-handler';
import Animated, { Easing, runOnJS, useAnimatedStyle, useSharedValue, withSpring, withTiming } from 'react-native-reanimated';
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
// How far (px) content travels off/on-screen during the actual tab-switch
// animation -- close to the drag threshold so release continues the
// motion the finger was already making, instead of jumping.
const EXIT_DISTANCE_PX = 90;
// Real-time drag-follow is capped here so a long drag doesn't fling
// content implausibly far while there's no second page rendered under it.
const DRAG_FOLLOW_MAX_PX = 70;
const EASE_OUT = Easing.out(Easing.cubic);

export function IPOListScreen({ navigation }: Props) {
  const [status, setStatus] = useState<IPOCatalogStatus>('open');
  const { data, isLoading, isError, refetch, isRefetching } = useIpoCatalog(status);

  const currentIndex = TABS.findIndex((t) => t.key === status);
  const fade = useSharedValue(1);
  const slide = useSharedValue(0);
  const isAnimating = useSharedValue(false);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: fade.value,
    transform: [{ translateX: slide.value }],
  }));

  // direction: +1 when the new tab is to the right (swiped left / tapped a
  // later tab), -1 when it's to the left. Continues sliding out in the
  // direction already being dragged, swaps the data once off-screen, then
  // slides + fades the new tab in from the opposite edge -- driven by
  // Reanimated shared values so the drag-follow in onUpdate below never
  // has to cross to the JS thread.
  const settleOnTab = (newStatus: IPOCatalogStatus, direction: 1 | -1) => {
    isAnimating.value = true;
    slide.value = withTiming(direction * EXIT_DISTANCE_PX, { duration: 180, easing: EASE_OUT });
    fade.value = withTiming(0, { duration: 150, easing: EASE_OUT }, () => {
      'worklet';
      runOnJS(setStatus)(newStatus);
      slide.value = -direction * EXIT_DISTANCE_PX;
      slide.value = withTiming(0, { duration: 240, easing: EASE_OUT });
      fade.value = withTiming(1, { duration: 240, easing: EASE_OUT }, () => {
        'worklet';
        isAnimating.value = false;
      });
    });
  };

  const snapBack = () => {
    isAnimating.value = true;
    slide.value = withSpring(0, { damping: 20, stiffness: 260, mass: 0.7 }, () => {
      'worklet';
      isAnimating.value = false;
    });
  };

  const changeTab = (newStatus: IPOCatalogStatus, direction: 1 | -1) => {
    if (newStatus === status || isAnimating.value) return;
    settleOnTab(newStatus, direction);
  };

  // activeOffsetX/failOffsetY let this only ever claim a predominantly
  // horizontal drag -- a vertical drag on the FlatList fails this gesture
  // immediately and falls through to the list's own native scrolling, so
  // swiping to switch tabs and scrolling the list never fight each other.
  // onUpdate runs entirely as a UI-thread worklet (no runOnJS) so the drag
  // stays responsive even while the JS thread is busy with a refetch or a
  // FlatList render; onEnd only crosses to JS for the two outcomes that
  // actually need it -- committing a tab change (a React state update) or
  // triggering the spring-back.
  const swipeGesture = Gesture.Pan()
    .activeOffsetX([-20, 20])
    .failOffsetY([-15, 15])
    .onUpdate((event: GestureUpdateEvent<PanGestureHandlerEventPayload>) => {
      'worklet';
      if (isAnimating.value) return;
      // Resistance at the ends (no earlier/later tab to reveal) so
      // dragging past the first/last tab feels like hitting a soft wall
      // instead of sliding away into nothing.
      const atStart = currentIndex === 0 && event.translationX > 0;
      const atEnd = currentIndex === TABS.length - 1 && event.translationX < 0;
      const resistance = atStart || atEnd ? 0.3 : 1;
      const target = event.translationX * resistance;
      slide.value = Math.max(-DRAG_FOLLOW_MAX_PX, Math.min(DRAG_FOLLOW_MAX_PX, target));
    })
    .onEnd((event: GestureStateChangeEvent<PanGestureHandlerEventPayload>) => {
      'worklet';
      if (isAnimating.value) return;
      if (event.translationX <= -SWIPE_THRESHOLD_PX && currentIndex < TABS.length - 1) {
        runOnJS(settleOnTab)(TABS[currentIndex + 1].key, 1);
      } else if (event.translationX >= SWIPE_THRESHOLD_PX && currentIndex > 0) {
        runOnJS(settleOnTab)(TABS[currentIndex - 1].key, -1);
      } else {
        runOnJS(snapBack)();
      }
    });

  return (
    <View style={styles.container}>
      <View style={styles.tabRow}>
        {TABS.map((tab, index) => (
          <TouchableOpacity key={tab.key} onPress={() => changeTab(tab.key, index > currentIndex ? 1 : -1)}>
            <Text style={[styles.tabLabel, status === tab.key && styles.tabLabelActive]}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <GestureDetector gesture={swipeGesture}>
        <Animated.View style={[styles.swipeArea, animatedStyle]}>
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
        </Animated.View>
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
  listContent: { paddingBottom: spacing.xl },
});

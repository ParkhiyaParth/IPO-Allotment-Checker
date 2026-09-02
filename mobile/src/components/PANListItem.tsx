import { memo } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import type { GestureStateChangeEvent, GestureUpdateEvent, PanGestureHandlerEventPayload } from 'react-native-gesture-handler';
import Animated, { FadeIn, FadeOut, LinearTransition, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import { maskPan } from '../utils/panMask';
import { PressableScale } from './PressableScale';
import type { PanProfile } from '../types/pan';

// How far (px) the card can be dragged left to reveal the delete action --
// exactly the action's own width, so a fully-open swipe lines up flush.
const DELETE_WIDTH = 88;
const SWIPE_OPEN_THRESHOLD = DELETE_WIDTH / 2;

export const PANListItem = memo(function PANListItem({
  profile,
  onPress,
  onDelete,
}: {
  profile: PanProfile;
  onPress: () => void;
  onDelete: () => void;
}) {
  const translateX = useSharedValue(0);

  const cardStyle = useAnimatedStyle(() => ({ transform: [{ translateX: translateX.value }] }));

  const close = () => {
    translateX.value = withTiming(0, { duration: 180 });
  };

  // failOffsetY hands a vertical drag straight back to the FlatList's own
  // scrolling, same pattern as the tab-swipe gesture on the IPO list.
  const swipeGesture = Gesture.Pan()
    .activeOffsetX([-10, 10])
    .failOffsetY([-10, 10])
    .onUpdate((event: GestureUpdateEvent<PanGestureHandlerEventPayload>) => {
      'worklet';
      translateX.value = Math.min(0, Math.max(-DELETE_WIDTH, event.translationX));
    })
    .onEnd((event: GestureStateChangeEvent<PanGestureHandlerEventPayload>) => {
      'worklet';
      const target = event.translationX < -SWIPE_OPEN_THRESHOLD ? -DELETE_WIDTH : 0;
      translateX.value = withTiming(target, { duration: 160 });
    });

  const handleSwipeDelete = () => {
    close();
    onDelete();
  };

  return (
    <Animated.View
      entering={FadeIn.duration(220)}
      exiting={FadeOut.duration(180)}
      layout={LinearTransition.duration(220)}
      style={styles.wrapper}
    >
      <View style={styles.deleteBackdrop}>
        <PressableScale style={styles.deleteAction} onPress={handleSwipeDelete}>
          <Text style={styles.deleteActionText}>Delete</Text>
        </PressableScale>
      </View>
      <GestureDetector gesture={swipeGesture}>
        <Animated.View style={cardStyle}>
          <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
            <View style={styles.info}>
              <Text style={styles.name}>{profile.name}</Text>
              <Text style={styles.pan}>{maskPan(profile.pan)}</Text>
            </View>
          </TouchableOpacity>
        </Animated.View>
      </GestureDetector>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  wrapper: {
    marginHorizontal: spacing.lg,
    marginVertical: spacing.xs,
  },
  deleteBackdrop: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    right: 0,
    width: DELETE_WIDTH,
    borderRadius: radii.md,
    backgroundColor: colors.statusNotAllotted,
    overflow: 'hidden',
  },
  deleteAction: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  deleteActionText: {
    color: colors.textOnPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  info: {
    flexShrink: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  pan: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    letterSpacing: 0.5,
  },
});

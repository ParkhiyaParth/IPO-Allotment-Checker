import type { ReactNode } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';
import { Pressable } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

const PRESS_SCALE = 0.96;
// Fast in, slightly slower out -- the interface should feel like it reacts
// instantly to touch, but releasing shouldn't feel twitchy.
const PRESS_IN_DURATION_MS = 80;
const PRESS_OUT_DURATION_MS = 120;

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export function PressableScale({
  onPress,
  style,
  children,
}: {
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
  children: ReactNode;
}) {
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <AnimatedPressable
      style={[style, animatedStyle]}
      onPress={onPress}
      onPressIn={() => {
        scale.value = withTiming(PRESS_SCALE, { duration: PRESS_IN_DURATION_MS });
      }}
      onPressOut={() => {
        scale.value = withTiming(1, { duration: PRESS_OUT_DURATION_MS });
      }}
    >
      {children}
    </AnimatedPressable>
  );
}

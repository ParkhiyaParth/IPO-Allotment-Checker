import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';

const BAR_HEIGHT_MAX = 24;
const BAR_HEIGHT_MIN = 3;

export function GmpSparkline({ trend }: { trend: (number | null)[] | null }) {
  const values = (trend ?? []).filter((v): v is number => v != null);
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;
  const delta = values[values.length - 1] - values[values.length - 2];

  return (
    <View style={styles.row}>
      <View style={styles.bars}>
        {values.map((value, i) => {
          const ratio = range === 0 ? 0.5 : (value - min) / range;
          const height = BAR_HEIGHT_MIN + ratio * (BAR_HEIGHT_MAX - BAR_HEIGHT_MIN);
          const isLast = i === values.length - 1;
          return (
            <View
              key={i}
              style={[
                styles.bar,
                {
                  height,
                  backgroundColor: isLast
                    ? value >= 0
                      ? colors.statusAllotted
                      : colors.statusNotAllotted
                    : colors.border,
                },
              ]}
            />
          );
        })}
      </View>
      {delta !== 0 ? (
        <Text style={[styles.delta, { color: delta > 0 ? colors.statusAllotted : colors.statusNotAllotted }]}>
          {delta > 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(0)}pt
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: spacing.xs, marginTop: spacing.xs },
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: 2 },
  bar: { width: 4, borderRadius: 2 },
  delta: { fontSize: 11, fontWeight: '700', marginLeft: spacing.xs },
});

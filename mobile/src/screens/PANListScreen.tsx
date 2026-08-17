import { Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { PANListItem } from '../components/PANListItem';
import { usePanProfiles } from '../hooks/usePanProfiles';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { PANsStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<PANsStackParamList, 'PANList'>;

export function PANListScreen({ navigation }: Props) {
  const { profiles, isLoading, removeProfile } = usePanProfiles();

  const confirmDelete = (id: string, name: string) => {
    Alert.alert('Remove PAN', `Remove ${name} from your saved list?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => removeProfile(id) },
    ]);
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.title}>My PANs</Text>
          <Text style={styles.subtitle}>Saved on this device only</Text>
        </View>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => navigation.navigate('AddEditPAN', undefined)}
        >
          <Text style={styles.addButtonText}>+ Add</Text>
        </TouchableOpacity>
      </View>

      {isLoading ? null : profiles.length === 0 ? (
        <EmptyState
          icon="🪪"
          title="Add your first PAN"
          subtitle="Tap + Add to save a name and PAN to check allotment against."
        />
      ) : (
        <FlatList
          data={profiles}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <PANListItem
              profile={item}
              onPress={() => navigation.navigate('AddEditPAN', { profileId: item.id })}
              onDelete={() => confirmDelete(item.id, item.name)}
            />
          )}
          contentContainerStyle={styles.listContent}
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
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
  addButton: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  addButtonText: {
    color: colors.textOnPrimary,
    fontWeight: '600',
    fontSize: 14,
  },
  listContent: {
    paddingBottom: spacing.xl,
  },
});

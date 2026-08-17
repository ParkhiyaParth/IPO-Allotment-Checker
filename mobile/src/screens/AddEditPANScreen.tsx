import { useState } from 'react';
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { usePanProfiles } from '../hooks/usePanProfiles';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import { isValidPan, normalizePan } from '../utils/panValidation';
import type { PANsStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<PANsStackParamList, 'AddEditPAN'>;

export function AddEditPANScreen({ route, navigation }: Props) {
  const profileId = route.params?.profileId;
  const { profiles, addProfile, updateProfile } = usePanProfiles();
  const existing = profiles.find((p) => p.id === profileId);

  const [name, setName] = useState(existing?.name ?? '');
  const [pan, setPan] = useState(existing?.pan ?? '');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const trimmedName = name.trim();
    const normalizedPan = normalizePan(pan);

    if (!trimmedName) {
      setError('Enter a name to label this PAN.');
      return;
    }
    if (!isValidPan(normalizedPan)) {
      setError('Enter a valid 10-character PAN (e.g. ABCDE1234F).');
      return;
    }

    setError(null);
    setSaving(true);
    try {
      if (existing) {
        await updateProfile({ id: existing.id, name: trimmedName, pan: normalizedPan });
      } else {
        await addProfile({ name: trimmedName, pan: normalizedPan });
      }
      navigation.goBack();
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Name</Text>
      <TextInput
        style={styles.input}
        value={name}
        onChangeText={setName}
        placeholder="e.g. Self, Spouse, Father"
        placeholderTextColor={colors.textSecondary}
      />

      <Text style={styles.label}>PAN</Text>
      <TextInput
        style={styles.input}
        value={pan}
        onChangeText={setPan}
        placeholder="ABCDE1234F"
        placeholderTextColor={colors.textSecondary}
        autoCapitalize="characters"
        maxLength={10}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity
        style={[styles.saveButton, saving && styles.saveButtonDisabled]}
        onPress={handleSave}
        disabled={saving}
      >
        <Text style={styles.saveButtonText}>{existing ? 'Save Changes' : 'Add PAN'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: spacing.xs,
    marginTop: spacing.lg,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    fontSize: 16,
    color: colors.textPrimary,
  },
  error: {
    color: colors.statusNotAllotted,
    fontSize: 13,
    marginTop: spacing.md,
  },
  saveButton: {
    backgroundColor: colors.primary,
    borderRadius: radii.md,
    paddingVertical: spacing.md,
    alignItems: 'center',
    marginTop: spacing.xl,
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    color: colors.textOnPrimary,
    fontWeight: '600',
    fontSize: 16,
  },
});

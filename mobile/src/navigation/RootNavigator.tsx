import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text } from 'react-native';
import { AddEditPANScreen } from '../screens/AddEditPANScreen';
import { IPODetailScreen } from '../screens/IPODetailScreen';
import { IPOListScreen } from '../screens/IPOListScreen';
import { PANListScreen } from '../screens/PANListScreen';
import { colors } from '../theme/colors';
import type { IPOsStackParamList, PANsStackParamList } from './types';

const IPOsStack = createNativeStackNavigator<IPOsStackParamList>();
const PANsStack = createNativeStackNavigator<PANsStackParamList>();
const Tab = createBottomTabNavigator();

const stackHeaderOptions = {
  headerStyle: { backgroundColor: colors.primary },
  headerTintColor: colors.textOnPrimary,
  headerTitleStyle: { fontWeight: '700' as const },
};

function IPOsStackNavigator() {
  return (
    <IPOsStack.Navigator screenOptions={stackHeaderOptions}>
      <IPOsStack.Screen name="IPOList" component={IPOListScreen} options={{ title: 'IPOs' }} />
      <IPOsStack.Screen
        name="IPODetail"
        component={IPODetailScreen}
        options={({ route }) => ({ title: route.params.companyName })}
      />
    </IPOsStack.Navigator>
  );
}

function PANsStackNavigator() {
  return (
    <PANsStack.Navigator screenOptions={stackHeaderOptions}>
      <PANsStack.Screen name="PANList" component={PANListScreen} options={{ title: 'My PANs' }} />
      <PANsStack.Screen
        name="AddEditPAN"
        component={AddEditPANScreen}
        options={({ route }) => ({ title: route.params?.profileId ? 'Edit PAN' : 'Add PAN' })}
      />
    </PANsStack.Navigator>
  );
}

export function RootNavigator() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.textSecondary,
        }}
      >
        <Tab.Screen
          name="IPOsTab"
          component={IPOsStackNavigator}
          options={{
            title: 'IPOs',
            tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>📈</Text>,
          }}
        />
        <Tab.Screen
          name="PANsTab"
          component={PANsStackNavigator}
          options={{
            title: 'My PANs',
            tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>🪪</Text>,
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

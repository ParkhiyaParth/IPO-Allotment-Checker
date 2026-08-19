import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Text } from 'react-native';
import { AddEditPANScreen } from '../screens/AddEditPANScreen';
import { AllotmentCheckScreen } from '../screens/AllotmentCheckScreen';
import { AllotmentListScreen } from '../screens/AllotmentListScreen';
import { ApplicationTimelineScreen } from '../screens/ApplicationTimelineScreen';
import { DeviceSyncScreen } from '../screens/DeviceSyncScreen';
import { FamilyPortfolioScreen } from '../screens/FamilyPortfolioScreen';
import { IPODetailScreen } from '../screens/IPODetailScreen';
import { IPOListScreen } from '../screens/IPOListScreen';
import { PANListScreen } from '../screens/PANListScreen';
import { colors } from '../theme/colors';
import type { AllotmentStackParamList, IPOsStackParamList, PANsStackParamList } from './types';

const IPOsStack = createNativeStackNavigator<IPOsStackParamList>();
const PANsStack = createNativeStackNavigator<PANsStackParamList>();
const AllotmentStack = createNativeStackNavigator<AllotmentStackParamList>();
const Tab = createBottomTabNavigator();

const stackHeaderOptions = {
  headerStyle: { backgroundColor: colors.primary },
  headerTintColor: colors.textOnPrimary,
  headerTitleStyle: { fontWeight: '700' as const },
  // Explicit even though it's the native-stack default -- swipe-back
  // (edge swipe / interactive pop) relies on GestureHandlerRootView
  // wrapping the app root (see App.tsx), which was missing before.
  gestureEnabled: true,
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
      <IPOsStack.Screen
        name="AllotmentCheck"
        component={AllotmentCheckScreen}
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
      <PANsStack.Screen
        name="DeviceSync"
        component={DeviceSyncScreen}
        options={{ title: 'Zero-Tap Allotment Check' }}
      />
    </PANsStack.Navigator>
  );
}

function AllotmentStackNavigator() {
  return (
    <AllotmentStack.Navigator screenOptions={stackHeaderOptions}>
      <AllotmentStack.Screen
        name="AllotmentList"
        component={AllotmentListScreen}
        options={{ title: 'Check Allotment' }}
      />
      <AllotmentStack.Screen
        name="AllotmentCheck"
        component={AllotmentCheckScreen}
        options={({ route }) => ({ title: route.params.companyName })}
      />
      <AllotmentStack.Screen
        name="FamilyPortfolio"
        component={FamilyPortfolioScreen}
        options={{ title: 'Family Portfolio' }}
      />
      <AllotmentStack.Screen
        name="ApplicationTimeline"
        component={ApplicationTimelineScreen}
        options={{ title: 'Application Timeline' }}
      />
    </AllotmentStack.Navigator>
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
          name="AllotmentTab"
          component={AllotmentStackNavigator}
          options={{
            title: 'Allotment',
            tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>✅</Text>,
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

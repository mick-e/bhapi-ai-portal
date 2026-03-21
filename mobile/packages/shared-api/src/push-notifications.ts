/**
 * Push notification registration and deep link handling for Expo mobile apps.
 * Manages Expo push token lifecycle and notification tap routing.
 */

import { ApiClient } from './rest-client';

export interface PushTokenResponse {
  id: string;
  token: string;
  device_type: 'ios' | 'android';
}

export interface PushNotificationData {
  alert_id?: string;
  severity?: string;
  post_id?: string;
  message_id?: string;
  contact_request_id?: string;
  screen?: string;
  [key: string]: string | undefined;
}

/**
 * Register for push notifications with the Bhapi backend.
 *
 * 1. Requests Expo push token from the device
 * 2. POSTs the token to the API for server-side storage
 *
 * Requires `expo-notifications` and `expo-device` to be installed.
 */
export async function registerForPushNotifications(
  apiClient: ApiClient,
  deviceType: 'ios' | 'android',
): Promise<PushTokenResponse | null> {
  try {
    // Dynamic imports so this module can be imported in test environments
    // without requiring native modules.
    const Notifications = await import('expo-notifications');
    const Device = await import('expo-device');

    if (!Device.isDevice) {
      console.warn('Push notifications require a physical device');
      return null;
    }

    // Request permission
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.warn('Push notification permission not granted');
      return null;
    }

    // Get Expo push token
    const tokenData = await Notifications.getExpoPushTokenAsync();
    const token = tokenData.data;

    // Register with backend
    const result = await apiClient.request<PushTokenResponse>(
      'POST',
      '/api/v1/alerts/push/token',
      { token, device_type: deviceType },
    );

    return result;
  } catch (error) {
    console.error('Failed to register for push notifications:', error);
    return null;
  }
}

/**
 * Unregister a push token from the backend.
 */
export async function unregisterPushToken(
  apiClient: ApiClient,
  token: string,
): Promise<void> {
  await apiClient.request('DELETE', '/api/v1/alerts/push/token', { token });
}

/**
 * Handle a notification tap and return the deep link route to navigate to.
 *
 * Maps notification data fields to app screens:
 * - alert_id → /alerts/:id
 * - post_id → /social/post/:id
 * - message_id → /messages/:id
 * - contact_request_id → /contacts/requests
 * - screen → direct route override
 */
export function resolveDeepLink(data: PushNotificationData): string | null {
  if (data.screen) {
    return data.screen;
  }
  if (data.alert_id) {
    return `/alerts/${data.alert_id}`;
  }
  if (data.post_id) {
    return `/social/post/${data.post_id}`;
  }
  if (data.message_id) {
    return `/messages/${data.message_id}`;
  }
  if (data.contact_request_id) {
    return '/contacts/requests';
  }
  return null;
}

/**
 * Set up notification response handler (call once in app root).
 * Returns a cleanup function to remove the listener.
 */
export function setupNotificationResponseHandler(
  onNavigate: (route: string) => void,
): () => void {
  let subscription: { remove: () => void } | null = null;

  (async () => {
    try {
      const Notifications = await import('expo-notifications');
      subscription = Notifications.addNotificationResponseReceivedListener(
        (response) => {
          const data = response.notification.request.content.data as PushNotificationData;
          const route = resolveDeepLink(data);
          if (route) {
            onNavigate(route);
          }
        },
      );
    } catch {
      // expo-notifications not available (e.g., web or test environment)
    }
  })();

  return () => {
    subscription?.remove();
  };
}

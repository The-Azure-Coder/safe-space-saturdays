import * as Notifications from 'expo-notifications'
import { Platform } from 'react-native'

Notifications.setNotificationHandler({ handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: false, shouldSetBadge: false }) })

export async function enableNotifications() {
  const current = await Notifications.getPermissionsAsync()
  let status = current.status
  if (status !== 'granted') status = (await Notifications.requestPermissionsAsync()).status
  if (status !== 'granted') return false
  if (Platform.OS === 'android') await Notifications.setNotificationChannelAsync('wellbeing', { name: 'Wellbeing reminders', importance: Notifications.AndroidImportance.DEFAULT })
  await Notifications.cancelScheduledNotificationAsync('safe-space-checkin').catch(() => undefined)
  await Notifications.scheduleNotificationAsync({ identifier: 'safe-space-checkin', content: { title: 'A gentle check-in', body: 'Take a moment to notice how you are doing today.', sound: false }, trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour: 18, minute: 30, ...(Platform.OS === 'android' ? { channelId: 'wellbeing' } : {}) } })
  return true
}

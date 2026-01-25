import { useNotificationStore } from '../stores/notificationStore';
import type { NotificationType } from '../stores/notificationStore';

export const useNotification = () => {
  const { addNotification } = useNotificationStore();

  const showSuccess = (message: string, duration?: number) => {
    addNotification(message, 'success', duration);
  };

  const showError = (message: string, duration?: number) => {
    addNotification(message, 'error', duration);
  };

  const showInfo = (message: string, duration?: number) => {
    addNotification(message, 'info', duration);
  };

  const showWarning = (message: string, duration?: number) => {
    addNotification(message, 'warning', duration);
  };

  const showNotification = (message: string, type?: NotificationType, duration?: number) => {
    addNotification(message, type, duration);
  };

  return {
    showSuccess,
    showError,
    showInfo,
    showWarning,
    showNotification,
  };
};

import { Snackbar, Alert, Box } from '@mui/material';
import type { AlertProps } from '@mui/material';
import { useNotificationStore } from '../../stores/notificationStore';
import { motion, AnimatePresence } from 'framer-motion';

const NotificationProvider = () => {
  const { notifications, removeNotification } = useNotificationStore();

  const getSeverity = (type: string): AlertProps['severity'] => {
    switch (type) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
      default:
        return 'info';
    }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 16,
        left: 16,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        maxWidth: '400px',
        pointerEvents: 'none',
      }}
    >
      <AnimatePresence>
        {notifications.map((notification, index) => (
          <motion.div
            key={notification.id}
            initial={{ opacity: 0, x: -100, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -100, scale: 0.8 }}
            transition={{
              type: 'spring',
              stiffness: 300,
              damping: 30,
            }}
            style={{
              pointerEvents: 'auto',
            }}
          >
            <Snackbar
              open={true}
              onClose={() => removeNotification(notification.id)}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
              sx={{
                position: 'relative',
                bottom: 'auto',
                left: 'auto',
                transform: 'none',
              }}
            >
              <Alert
                onClose={() => removeNotification(notification.id)}
                severity={getSeverity(notification.type)}
                variant="filled"
                sx={{
                  minWidth: '300px',
                  backgroundColor: notification.type === 'success' 
                    ? '#2e7d32' 
                    : notification.type === 'error'
                    ? '#d32f2f'
                    : notification.type === 'warning'
                    ? '#ed6c02'
                    : '#0288d1',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                  borderRadius: '12px',
                  '& .MuiAlert-icon': {
                    color: '#fff',
                  },
                  '& .MuiAlert-message': {
                    color: '#fff',
                    fontWeight: 500,
                  },
                }}
              >
                {notification.message}
              </Alert>
            </Snackbar>
          </motion.div>
        ))}
      </AnimatePresence>
    </Box>
  );
};

export default NotificationProvider;

import { Box, Drawer, Typography, IconButton, List, ListItem, ListItemText, Divider, Button } from '@mui/material';
import { Close as CloseIcon, CheckCircle as CheckCircleIcon } from '@mui/icons-material';
import { useNotificationStore } from '../../stores/notificationStore';
import { motion, AnimatePresence } from 'framer-motion';

interface NotificationsPanelProps {
  open: boolean;
  onClose: () => void;
}

const NotificationsPanel = ({ open, onClose }: NotificationsPanelProps) => {
  const { notifications, removeNotification, clearNotifications } = useNotificationStore();

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'success':
        return '#2e7d32';
      case 'error':
        return '#d32f2f';
      case 'warning':
        return '#ed6c02';
      case 'info':
      default:
        return '#0288d1';
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return '✓';
      case 'error':
        return '✕';
      case 'warning':
        return '⚠';
      case 'info':
      default:
        return 'ℹ';
    }
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: 380,
          backgroundColor: '#12182B',
          borderLeft: '1px solid rgba(0, 217, 255, 0.2)',
        },
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header */}
        <Box
          sx={{
            px: 2.5,
            py: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(0, 217, 255, 0.1)',
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 600, color: '#FF6B9D' }}>
            Notifications
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {notifications.length > 0 && (
              <Button
                size="small"
                onClick={clearNotifications}
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  minWidth: 'auto',
                  px: 1,
                }}
              >
                Tout effacer
              </Button>
            )}
            <IconButton
              size="small"
              onClick={onClose}
              sx={{ color: 'text.secondary' }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          {notifications.length === 0 ? (
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                p: 3,
                textAlign: 'center',
              }}
            >
              <CheckCircleIcon
                sx={{
                  fontSize: 64,
                  color: 'text.disabled',
                  mb: 2,
                  opacity: 0.5,
                }}
              />
              <Typography variant="body1" color="text.secondary">
                Aucune notification
              </Typography>
              <Typography variant="caption" color="text.disabled" sx={{ mt: 1 }}>
                Les notifications apparaîtront ici
              </Typography>
            </Box>
          ) : (
            <List sx={{ p: 0 }}>
              <AnimatePresence>
                {notifications.map((notification, index) => (
                  <motion.div
                    key={notification.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                  >
                    <ListItem
                      sx={{
                        px: 2.5,
                        py: 1.5,
                        borderLeft: `3px solid ${getNotificationColor(notification.type)}`,
                        backgroundColor: 'rgba(0, 217, 255, 0.02)',
                        '&:hover': {
                          backgroundColor: 'rgba(0, 217, 255, 0.05)',
                        },
                      }}
                    >
                      <Box
                        sx={{
                          width: 32,
                          height: 32,
                          borderRadius: '50%',
                          backgroundColor: `${getNotificationColor(notification.type)}20`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          mr: 2,
                          flexShrink: 0,
                          color: getNotificationColor(notification.type),
                          fontWeight: 600,
                          fontSize: '0.875rem',
                        }}
                      >
                        {getNotificationIcon(notification.type)}
                      </Box>
                      <ListItemText
                        primary={notification.message}
                        primaryTypographyProps={{
                          variant: 'body2',
                          sx: {
                            color: 'text.primary',
                            fontWeight: 500,
                          },
                        }}
                        secondary={
                          <Typography
                            variant="caption"
                            sx={{
                              color: 'text.secondary',
                              mt: 0.5,
                              display: 'block',
                            }}
                          >
                            {notification.type === 'success' && 'Succès'}
                            {notification.type === 'error' && 'Erreur'}
                            {notification.type === 'warning' && 'Avertissement'}
                            {notification.type === 'info' && 'Information'}
                          </Typography>
                        }
                      />
                      <IconButton
                        size="small"
                        onClick={() => removeNotification(notification.id)}
                        sx={{
                          color: 'text.secondary',
                          ml: 1,
                          '&:hover': {
                            color: 'text.primary',
                          },
                        }}
                      >
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    </ListItem>
                    {index < notifications.length - 1 && (
                      <Divider sx={{ borderColor: 'rgba(0, 217, 255, 0.1)' }} />
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </List>
          )}
        </Box>
      </Box>
    </Drawer>
  );
};

export default NotificationsPanel;

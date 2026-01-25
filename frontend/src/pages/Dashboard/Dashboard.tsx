import { useState } from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Avatar,
  Divider,
  Tooltip,
  Badge,
} from '@mui/material';
import { useNotificationStore } from '../../stores/notificationStore';
import NotificationsPanel from '../../components/Notifications/NotificationsPanel';
import {
  AccountTree as MindmapIcon,
  Dashboard as DashboardIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  BoltOutlined as TriggerIcon,
  History as HistoryIcon,
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import MindmapCanvas from '../../components/Mindmap/MindmapCanvas';
import TextInput from '../../components/Mindmap/TextInput';
import NodeDetails from '../../components/Mindmap/NodeDetails';
import MindmapSelector from '../../components/Mindmap/MindmapSelector';
import AgentsList from '../../components/Agents/AgentsList';
import HistoryPanel from '../../components/History/HistoryPanel';
import Overview from '../../components/Overview/Overview';
import Settings from '../Settings/Settings';
import { useAuthStore } from '../../stores/authStore';
import { useMindmapStore } from '../../stores/mindmapStore';

const drawerWidth = 260;
const collapsedWidth = 72;

const menuItems = [
  { icon: <DashboardIcon />, label: 'Vue d\'ensemble', id: 'overview' },
  { icon: <MindmapIcon />, label: 'Mindmap', id: 'mindmap' },
  { icon: <TriggerIcon />, label: 'Automatisations', id: 'automations' },
  { icon: <HistoryIcon />, label: 'Historique', id: 'history' },
  { icon: <SettingsIcon />, label: 'Paramètres', id: 'settings' },
];

const Dashboard = () => {
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);
  const [activeView, setActiveView] = useState('mindmap');
  const [notificationsPanelOpen, setNotificationsPanelOpen] = useState(false);
  const { user } = useAuthStore();
  const { selectedNode } = useMindmapStore();
  const { notifications } = useNotificationStore();

  const toggleDrawer = () => {
    setIsDrawerOpen(!isDrawerOpen);
  };

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
      {/* Sidebar */}
      <Drawer
        variant="permanent"
        sx={{
          width: isDrawerOpen ? drawerWidth : collapsedWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: isDrawerOpen ? drawerWidth : collapsedWidth,
            boxSizing: 'border-box',
            top: { xs: 56, md: 64 },
            height: 'calc(100% - 64px)',
            backgroundColor: '#12182B',
            borderRight: '1px solid rgba(0, 217, 255, 0.1)',
            transition: 'width 0.3s ease',
            overflowX: 'hidden',
          },
        }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Toggle Button */}
          <Box sx={{ p: 1.5, display: 'flex', justifyContent: isDrawerOpen ? 'flex-end' : 'center' }}>
            <IconButton
              onClick={toggleDrawer}
              sx={{
                color: 'text.secondary',
                '&:hover': { color: 'primary.main' },
              }}
            >
              {isDrawerOpen ? <ChevronLeftIcon /> : <MenuIcon />}
            </IconButton>
          </Box>

          {/* User Info */}
          <Box sx={{ px: 2, pb: 2 }}>
            <AnimatePresence>
              {isDrawerOpen ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      background: 'rgba(0, 217, 255, 0.05)',
                      border: '1px solid rgba(0, 217, 255, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1.5,
                    }}
                  >
                    <Avatar
                      sx={{
                        width: 40,
                        height: 40,
                        backgroundColor: '#00D9FF',
                        fontWeight: 600,
                      }}
                    >
                      {user?.name?.charAt(0).toUpperCase()}
                    </Avatar>
                    <Box sx={{ overflow: 'hidden' }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {user?.name}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}
                      >
                        {user?.email}
                      </Typography>
                    </Box>
                  </Box>
                </motion.div>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  <Avatar
                    sx={{
                      width: 40,
                      height: 40,
                      background: 'linear-gradient(135deg, #00D9FF 0%, #0066FF 100%)',
                      fontWeight: 600,
                    }}
                  >
                    {user?.name?.charAt(0).toUpperCase()}
                  </Avatar>
                </Box>
              )}
            </AnimatePresence>
          </Box>

          <Divider sx={{ borderColor: 'rgba(0, 217, 255, 0.1)' }} />

          {/* Menu Items */}
          <List sx={{ flex: 1, pt: 2 }}>
            {menuItems.map((item, index) => (
              <ListItem key={item.id} disablePadding sx={{ px: 1.5, mb: 0.5 }}>
                <Tooltip title={!isDrawerOpen ? item.label : ''} placement="right">
                  <ListItemButton
                    onClick={() => setActiveView(item.id)}
                    sx={{
                      borderRadius: '12px',
                      minHeight: 48,
                      justifyContent: isDrawerOpen ? 'initial' : 'center',
                      background: activeView === item.id ? 'rgba(0, 217, 255, 0.1)' : 'transparent',
                      border: activeView === item.id ? '1px solid rgba(0, 217, 255, 0.2)' : '1px solid transparent',
                      '&:hover': {
                        background: 'rgba(0, 217, 255, 0.08)',
                      },
                    }}
                  >
                    <ListItemIcon
                      sx={{
                        minWidth: 0,
                        mr: isDrawerOpen ? 2 : 0,
                        justifyContent: 'center',
                        color: activeView === item.id ? 'primary.main' : 'text.secondary',
                      }}
                    >
                      <motion.div
                        initial={{ scale: 1 }}
                        whileHover={{ scale: 1.1 }}
                        transition={{ type: 'spring', stiffness: 400 }}
                      >
                        {item.icon}
                      </motion.div>
                    </ListItemIcon>
                    {isDrawerOpen && (
                      <ListItemText
                        primary={item.label}
                        primaryTypographyProps={{
                          fontSize: '0.9rem',
                          fontWeight: activeView === item.id ? 600 : 400,
                          color: activeView === item.id ? 'primary.main' : 'text.primary',
                        }}
                      />
                    )}
                  </ListItemButton>
                </Tooltip>
              </ListItem>
            ))}
          </List>

          {/* Notifications */}
          <Box sx={{ p: 2 }}>
            <Tooltip title={!isDrawerOpen ? 'Notifications' : ''} placement="right">
              <IconButton
                onClick={() => setNotificationsPanelOpen(true)}
                sx={{
                  width: isDrawerOpen ? '100%' : 40,
                  height: 40,
                  borderRadius: '12px',
                  background: 'rgba(255, 107, 157, 0.1)',
                  border: '1px solid rgba(255, 107, 157, 0.2)',
                  display: 'flex',
                  justifyContent: isDrawerOpen ? 'flex-start' : 'center',
                  px: isDrawerOpen ? 2 : 0,
                  gap: 2,
                  '&:hover': {
                    background: 'rgba(255, 107, 157, 0.15)',
                  },
                }}
              >
                <Badge 
                  badgeContent={notifications.length > 0 ? notifications.length : 0} 
                  color="secondary"
                  sx={{
                    '& .MuiBadge-badge': {
                      backgroundColor: '#FF6B9D',
                      color: '#fff',
                    },
                  }}
                >
                  <NotificationsIcon sx={{ color: '#FF6B9D' }} />
                </Badge>
                {isDrawerOpen && (
                  <Typography variant="body2" sx={{ color: '#FF6B9D', fontWeight: 500 }}>
                    Notifications
                  </Typography>
                )}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Drawer>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: '#0A0E17',
          height: '100%',
        }}
      >
        {activeView === 'mindmap' && (
          <>
            {/* Sélecteur de mindmap en haut */}
            <Box
              sx={{
                position: 'absolute',
                top: 16,
                left: 0,
                right: 0,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                zIndex: 20,
                pointerEvents: 'none',
              }}
            >
              <Box sx={{ pointerEvents: 'auto' }}>
                <MindmapSelector />
              </Box>
            </Box>
            <TextInput />
            <MindmapCanvas />
            {selectedNode && <NodeDetails />}
          </>
        )}

        {activeView === 'overview' && (
          <Overview
            onSelectMindmap={(mindmapId) => {
              setActiveView('mindmap');
            }}
          />
        )}

        {activeView === 'automations' && (
          <Box
            sx={{
              height: '100%',
              overflow: 'auto',
              p: 2,
            }}
          >
            <AgentsList />
          </Box>
        )}

        {activeView === 'history' && (
          <Box
            sx={{
              height: '100%',
              overflow: 'auto',
              p: 2,
            }}
          >
            <HistoryPanel />
          </Box>
        )}

        {activeView === 'settings' && (
          <Box sx={{ height: '100%', overflow: 'auto' }}>
            <Settings />
          </Box>
        )}
      </Box>

      {/* Notifications Panel */}
      <NotificationsPanel
        open={notificationsPanelOpen}
        onClose={() => setNotificationsPanelOpen(false)}
      />
    </Box>
  );
};

export default Dashboard;

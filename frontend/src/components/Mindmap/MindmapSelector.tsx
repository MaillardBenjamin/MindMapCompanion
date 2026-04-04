import { useState, useEffect } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  IconButton,
  Typography,
  Chip,
  CircularProgress,
  Alert,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Add as AddIcon,
  AccountTree as MindmapIcon,
  MoreVert as MoreIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useMindmapStore } from '../../stores/mindmapStore';
import type { MindmapResponse } from '../../services/api';

const MindmapSelector = () => {
  const [open, setOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedMindmapForMenu, setSelectedMindmapForMenu] = useState<MindmapResponse | null>(null);
  const [newMindmapName, setNewMindmapName] = useState('');
  const [newMindmapDescription, setNewMindmapDescription] = useState('');
  const [editMindmapName, setEditMindmapName] = useState('');
  const [editMindmapDescription, setEditMindmapDescription] = useState('');
  const [isUpdatingMindmap, setIsUpdatingMindmap] = useState(false);

  const {
    mindmaps,
    currentMindmap,
    isLoadingMindmaps,
    error,
    loadMindmaps,
    createMindmap,
    selectMindmap,
    deleteMindmap,
    updateMindmap,
    clearError,
  } = useMindmapStore();

  useEffect(() => {
    if (open && mindmaps.length === 0) {
      loadMindmaps();
    }
  }, [open, mindmaps.length, loadMindmaps]);

  const handleOpen = () => {
    setOpen(true);
    loadMindmaps();
  };

  const handleCreate = async () => {
    if (!newMindmapName.trim()) return;

    clearError();
    const created = await createMindmap(newMindmapName, newMindmapDescription || undefined);
    if (created) {
      setCreateDialogOpen(false);
      setNewMindmapName('');
      setNewMindmapDescription('');
      setOpen(false);
    }
  };

  const handleSelect = async (mindmap: MindmapResponse) => {
    if (mindmap.id === currentMindmap?.id) {
      setOpen(false);
      return;
    }

    clearError();
    await selectMindmap(mindmap.id);
    setOpen(false);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, mindmap: MindmapResponse) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
    setSelectedMindmapForMenu(mindmap);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleDeleteClick = () => {
    // Fermer le menu mais conserver selectedMindmapForMenu pour le dialog
    setMenuAnchor(null);
    setDeleteDialogOpen(true);
  };

  const handleEditClick = () => {
    if (!selectedMindmapForMenu) return;
    setMenuAnchor(null);
    setEditMindmapName(selectedMindmapForMenu.name || '');
    setEditMindmapDescription(selectedMindmapForMenu.description || '');
    setEditDialogOpen(true);
  };

  const handleEditConfirm = async () => {
    if (!selectedMindmapForMenu) return;
    if (!editMindmapName.trim()) return;
    if (isUpdatingMindmap) return;

    setIsUpdatingMindmap(true);
    clearError();
    try {
      await updateMindmap(
        selectedMindmapForMenu.id,
        editMindmapName.trim(),
        editMindmapDescription.trim() || undefined
      );
      await loadMindmaps();
      setEditDialogOpen(false);
      setSelectedMindmapForMenu(null);
    } finally {
      setIsUpdatingMindmap(false);
    }
  };

  const handleEditCancel = () => {
    setEditDialogOpen(false);
    setEditMindmapName('');
    setEditMindmapDescription('');
    setSelectedMindmapForMenu(null);
    clearError();
  };

  const handleDeleteConfirm = async () => {
    if (!selectedMindmapForMenu) return;

    clearError();
    await deleteMindmap(selectedMindmapForMenu.id);
    setDeleteDialogOpen(false);
    setSelectedMindmapForMenu(null);
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setSelectedMindmapForMenu(null);
  };

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<MindmapIcon />}
        onClick={handleOpen}
        sx={{ minWidth: 200, justifyContent: 'flex-start' }}
      >
        {currentMindmap ? currentMindmap.name : 'Sélectionner un mindmap'}
      </Button>

      {/* Dialog de sélection */}
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
          clearError();
        }}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: '#12182B',
            border: '1px solid rgba(0, 217, 255, 0.2)',
          },
        }}
      >
        <DialogTitle sx={{ color: 'text.primary', pb: 1 }}>
          Mes Mindmaps
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
              {error}
            </Alert>
          )}

          {isLoadingMindmaps ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              {mindmaps.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <MindmapIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2, opacity: 0.5 }} />
                  <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                    Aucun mindmap créé
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => {
                      setOpen(false);
                      setCreateDialogOpen(true);
                    }}
                  >
                    Créer mon premier mindmap
                  </Button>
                </Box>
              ) : (
                <List sx={{ p: 0 }}>
                  <AnimatePresence>
                    {mindmaps.map((mindmap) => (
                      <motion.div
                        key={mindmap.id}
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                      >
                        <ListItem
                          disablePadding
                          secondaryAction={
                            <IconButton
                              edge="end"
                              onClick={(e) => handleMenuOpen(e, mindmap)}
                              sx={{ color: 'text.secondary' }}
                            >
                              <MoreIcon />
                            </IconButton>
                          }
                        >
                          <ListItemButton
                            onClick={() => handleSelect(mindmap)}
                            selected={currentMindmap?.id === mindmap.id}
                            sx={{
                              borderRadius: '12px',
                              mb: 1,
                              '&.Mui-selected': {
                                backgroundColor: 'rgba(0, 217, 255, 0.1)',
                                border: '1px solid rgba(0, 217, 255, 0.3)',
                              },
                            }}
                          >
                            <ListItemIcon sx={{ minWidth: 40 }}>
                              {currentMindmap?.id === mindmap.id ? (
                                <CheckIcon sx={{ color: 'primary.main' }} />
                              ) : (
                                <MindmapIcon sx={{ color: 'text.secondary' }} />
                              )}
                            </ListItemIcon>
                            <ListItemText
                              primary={mindmap.name}
                              secondary={mindmap.description || 'Aucune description'}
                              primaryTypographyProps={{
                                fontWeight: currentMindmap?.id === mindmap.id ? 600 : 400,
                                color: currentMindmap?.id === mindmap.id ? 'primary.main' : 'text.primary',
                              }}
                            />
                          </ListItemButton>
                        </ListItem>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </List>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            variant="outlined"
            onClick={() => {
              setOpen(false);
              clearError();
            }}
          >
            Annuler
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setOpen(false);
              setCreateDialogOpen(true);
            }}
          >
            Nouveau mindmap
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog de création */}
      <Dialog
        open={createDialogOpen}
        onClose={() => {
          setCreateDialogOpen(false);
          setNewMindmapName('');
          setNewMindmapDescription('');
          clearError();
        }}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: '#12182B',
            border: '1px solid rgba(0, 217, 255, 0.2)',
          },
        }}
      >
        <DialogTitle sx={{ color: 'text.primary' }}>
          Créer un nouveau mindmap
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
              {error}
            </Alert>
          )}
          <TextField
            fullWidth
            label="Nom du mindmap"
            value={newMindmapName}
            onChange={(e) => setNewMindmapName(e.target.value)}
            sx={{ mb: 2, mt: 2 }}
            required
            autoFocus
          />
          <TextField
            fullWidth
            label="Description (optionnel)"
            value={newMindmapDescription}
            onChange={(e) => setNewMindmapDescription(e.target.value)}
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            variant="outlined"
            onClick={() => {
              setCreateDialogOpen(false);
              setNewMindmapName('');
              setNewMindmapDescription('');
              clearError();
            }}
          >
            Annuler
          </Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!newMindmapName.trim()}
          >
            Créer
          </Button>
        </DialogActions>
      </Dialog>

      {/* Menu contextuel */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: {
            backgroundColor: '#12182B',
            border: '1px solid rgba(0, 217, 255, 0.2)',
            minWidth: 150,
          },
        }}
      >
        <MenuItem
          onClick={() => {
            handleEditClick();
          }}
          sx={{ color: 'text.primary' }}
        >
          <EditIcon sx={{ mr: 1, fontSize: 18 }} />
          Modifier
        </MenuItem>
        <MenuItem
          onClick={handleDeleteClick}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon sx={{ mr: 1, fontSize: 18 }} />
          Supprimer
        </MenuItem>
      </Menu>

      {/* Dialog d'édition */}
      <Dialog
        open={editDialogOpen}
        onClose={handleEditCancel}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: '#12182B',
            border: '1px solid rgba(0, 217, 255, 0.2)',
          },
        }}
      >
        <DialogTitle sx={{ color: 'text.primary' }}>
          Modifier le mindmap
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
              {error}
            </Alert>
          )}
          <TextField
            fullWidth
            label="Nom du mindmap"
            value={editMindmapName}
            onChange={(e) => setEditMindmapName(e.target.value)}
            sx={{ mb: 2, mt: 2 }}
            required
            autoFocus
          />
          <TextField
            fullWidth
            label="Description (optionnel)"
            value={editMindmapDescription}
            onChange={(e) => setEditMindmapDescription(e.target.value)}
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button variant="outlined" onClick={handleEditCancel}>
            Annuler
          </Button>
          <Button
            variant="contained"
            onClick={handleEditConfirm}
            disabled={!editMindmapName.trim() || isUpdatingMindmap}
          >
            Enregistrer
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog de confirmation de suppression */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: '#12182B',
            border: '1px solid rgba(0, 217, 255, 0.2)',
          },
        }}
      >
        <DialogTitle sx={{ color: 'text.primary', pb: 1 }}>
          Confirmer la suppression
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
              {error}
            </Alert>
          )}
          <Typography variant="body1" sx={{ color: 'text.primary', mb: 1 }}>
            Êtes-vous sûr de vouloir supprimer le mindmap{' '}
            {selectedMindmapForMenu?.name ? (
              <strong style={{ color: '#00D9FF' }}>"{selectedMindmapForMenu.name}"</strong>
            ) : (
              <strong style={{ color: '#00D9FF' }}>sélectionné</strong>
            )}
            {' '}?
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Cette action est irréversible. Tous les nœuds et triggers associés seront également supprimés.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            variant="outlined"
            onClick={handleDeleteCancel}
          >
            Annuler
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleDeleteConfirm}
            sx={{
              backgroundColor: '#FF5757',
              '&:hover': {
                backgroundColor: '#FF3333',
              },
            }}
          >
            Supprimer
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default MindmapSelector;

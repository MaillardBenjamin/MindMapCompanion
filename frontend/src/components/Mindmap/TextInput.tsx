import { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  CircularProgress,
  Typography,
  IconButton,
  Collapse,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Psychology as ReorganizeIcon,
  DragIndicator as DragIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useMindmapStore } from '../../stores/mindmapStore';
import { useNotification } from '../../hooks/useNotification';

const STORAGE_KEY_POSITION = 'assistant-ia-position';
const STORAGE_KEY_EXPANDED = 'assistant-ia-expanded';

const TextInput = () => {
  const [text, setText] = useState('');
  const [isExpanded, setIsExpanded] = useState(() => {
    // Charger l'état depuis le localStorage
    const saved = localStorage.getItem(STORAGE_KEY_EXPANDED);
    return saved !== null ? saved === 'true' : true;
  });
  const [position, setPosition] = useState(() => {
    // Charger la position depuis le localStorage
    const saved = localStorage.getItem(STORAGE_KEY_POSITION);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed && typeof parsed.x === 'number' && typeof parsed.y === 'number') {
          return { x: parsed.x, y: parsed.y };
        }
      } catch (e) {
        console.warn('Erreur lors du chargement de la position sauvegardée:', e);
      }
    }
    return { x: 0, y: 16 };
  });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const positionRef = useRef(position);
  const { processText, reorganizeMindmapWithAI, isProcessing, currentMindmap, nodes } = useMindmapStore();
  const { showSuccess, showError, showInfo } = useNotification();

  // Mettre à jour la ref quand la position change
  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  // Sauvegarder l'état expanded dans le localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_EXPANDED, String(isExpanded));
  }, [isExpanded]);

  // Sauvegarder la position dans le localStorage quand elle change
  useEffect(() => {
    if (position.x !== 0 || position.y !== 16) {
      localStorage.setItem(STORAGE_KEY_POSITION, JSON.stringify(position));
    }
  }, [position]);

  // Valider et ajuster la position sauvegardée au montage et lors du redimensionnement
  useEffect(() => {
    const validateAndAdjustPosition = () => {
      if (containerRef.current) {
        // Essayer d'obtenir le conteneur parent
        let parent: HTMLElement | null = containerRef.current.offsetParent as HTMLElement;
        
        if (!parent || parent === document.body) {
          let current = containerRef.current.parentElement;
          while (current && current !== document.body) {
            const style = window.getComputedStyle(current);
            if (style.position === 'relative' || style.position === 'absolute' || style.position === 'fixed') {
              parent = current;
              break;
            }
            current = current.parentElement;
          }
        }
        
        // Utiliser la ref pour obtenir la position actuelle sans créer de dépendance
        const currentPos = positionRef.current;
        
        if (parent) {
          const containerWidth = parent.clientWidth;
          const containerHeight = parent.clientHeight;
          const panelWidth = 420;
          const panelHeight = containerRef.current.offsetHeight || 200; // Estimation si pas encore rendu
          
          // Si la position est la position par défaut (0, 16), calculer une position initiale
          if (currentPos.x === 0 && currentPos.y === 16) {
            const newX = containerWidth - panelWidth - 16;
            setPosition({ x: Math.max(16, newX), y: 16 });
          } else {
            // Valider que la position sauvegardée est dans les limites
            const maxX = containerWidth - panelWidth - 16;
            const maxY = containerHeight - panelHeight - 16;
            const adjustedX = Math.max(16, Math.min(maxX, currentPos.x));
            const adjustedY = Math.max(16, Math.min(maxY, currentPos.y));
            
            if (adjustedX !== currentPos.x || adjustedY !== currentPos.y) {
              setPosition({ x: adjustedX, y: adjustedY });
            }
          }
        } else {
          // Fallback : utiliser la largeur de la fenêtre moins une estimation du drawer
          const estimatedDrawerWidth = 260;
          const containerWidth = window.innerWidth - estimatedDrawerWidth;
          const containerHeight = window.innerHeight;
          const panelWidth = 420;
          const panelHeight = containerRef.current.offsetHeight || 200;
          
          if (currentPos.x === 0 && currentPos.y === 16) {
            setPosition({ x: Math.max(16, containerWidth - panelWidth - 16), y: 16 });
          } else {
            // Valider que la position sauvegardée est dans les limites
            const maxX = containerWidth - panelWidth - 16;
            const maxY = containerHeight - panelHeight - 16;
            const adjustedX = Math.max(16, Math.min(maxX, currentPos.x));
            const adjustedY = Math.max(16, Math.min(maxY, currentPos.y));
            
            if (adjustedX !== currentPos.x || adjustedY !== currentPos.y) {
              setPosition({ x: adjustedX, y: adjustedY });
            }
          }
        }
      }
    };
    
    // Initialiser après un court délai pour que le DOM soit prêt
    const timer = setTimeout(validateAndAdjustPosition, 100);
    
    // Mettre à jour si la fenêtre est redimensionnée
    window.addEventListener('resize', validateAndAdjustPosition);
    
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', validateAndAdjustPosition);
    };
  }, []); // Exécuter seulement au montage

  // Gérer le drag
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && containerRef.current) {
        // Trouver le conteneur parent
        let parent: HTMLElement | null = containerRef.current.offsetParent as HTMLElement;
        
        if (!parent || parent === document.body) {
          let current = containerRef.current.parentElement;
          while (current && current !== document.body) {
            const style = window.getComputedStyle(current);
            if (style.position === 'relative' || style.position === 'absolute' || style.position === 'fixed') {
              parent = current;
              break;
            }
            current = current.parentElement;
          }
        }
        
        if (parent && containerRef.current) {
          const parentRect = parent.getBoundingClientRect();
          const containerWidth = parent.clientWidth;
          const containerHeight = parent.clientHeight;
          const panelWidth = 420;
          
          // Utiliser la hauteur réelle du panneau selon son état (déplié ou non)
          const panelHeight = containerRef.current.offsetHeight;
          
          // Calculer la position relative au conteneur parent
          const relativeX = e.clientX - parentRect.left - dragOffset.x;
          const relativeY = e.clientY - parentRect.top - dragOffset.y;
          
          // Limiter aux limites du conteneur
          const maxX = containerWidth - panelWidth - 16;
          const maxY = containerHeight - panelHeight - 16;
          const newX = Math.max(16, Math.min(maxX, relativeX));
          const newY = Math.max(16, Math.min(maxY, relativeY));
          
          setPosition({ x: newX, y: newY });
        }
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset, isExpanded]);

  const handleDragStart = (e: React.MouseEvent) => {
    if (containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      
      // Calculer l'offset de la souris par rapport au coin supérieur gauche du conteneur
      const offsetX = e.clientX - containerRect.left;
      const offsetY = e.clientY - containerRect.top;
      
      setDragOffset({
        x: offsetX,
        y: offsetY,
      });
      setIsDragging(true);
    }
    e.preventDefault();
    e.stopPropagation();
  };

  const handleSubmit = async () => {
    if (!text.trim() || isProcessing) return;
    try {
      showInfo('Analyse du texte en cours...');
      await processText(text);
      setText('');
      showSuccess('Texte analysé avec succès');
    } catch (error) {
      console.error('Erreur lors du traitement du texte:', error);
      showError('Erreur lors de l\'analyse du texte');
    }
  };

  const handleReorganize = async () => {
    if (isProcessing || !currentMindmap || nodes.length === 0) return;
    try {
      showInfo('Réorganisation du mindmap en cours...');
      await reorganizeMindmapWithAI();
      showSuccess('Mindmap réorganisé avec succès');
    } catch (error) {
      console.error('Erreur lors de la réorganisation:', error);
      showError('Erreur lors de la réorganisation du mindmap');
    }
  };

  const placeholderTexts = [
    'Décrivez votre projet ou vos idées...',
    'Ex: "Je veux organiser mon travail en sprints avec des tâches quotidiennes..."',
    'Ex: "Créer un plan marketing avec SEO, réseaux sociaux et email..."',
  ];

  return (
    <Box
      ref={containerRef}
      sx={{
        position: 'absolute',
        top: `${position.y}px`,
        left: `${position.x}px`,
        zIndex: 15,
        width: 420,
        maxWidth: 'calc(100% - 32px)',
        pointerEvents: 'auto',
        cursor: isDragging ? 'grabbing' : 'default',
        userSelect: 'none',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box
          sx={{
            backgroundColor: '#12182B',
            backdropFilter: 'blur(20px)',
            borderRadius: '16px',
            border: '1px solid rgba(0, 217, 255, 0.2)',
            overflow: 'hidden',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          }}
        >
          {/* Header */}
          <Box
            sx={{
              px: 2,
              py: 1.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: isExpanded ? '1px solid rgba(0, 217, 255, 0.1)' : 'none',
            }}
          >
            <Box 
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1.5,
                flex: 1,
                cursor: 'pointer',
              }}
              onClick={() => setIsExpanded(!isExpanded)}
            >
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: '8px',
                  backgroundColor: '#00D9FF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <AIIcon sx={{ fontSize: 18, color: '#0A0E17' }} />
              </Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Assistant IA
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <IconButton
                size="small"
                sx={{
                  color: 'text.secondary',
                  cursor: 'grab',
                  '&:active': { cursor: 'grabbing' },
                }}
                onMouseDown={handleDragStart}
              >
                <DragIcon sx={{ fontSize: 18 }} />
              </IconButton>
              <IconButton 
                size="small" 
                sx={{ color: 'text.secondary' }}
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? <CollapseIcon /> : <ExpandIcon />}
              </IconButton>
            </Box>
          </Box>

          {/* Content */}
          <Collapse in={isExpanded}>
            <Box sx={{ p: 2 }}>
              <TextField
                fullWidth
                multiline
                rows={3}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={placeholderTexts[0]}
                disabled={isProcessing}
                sx={{
                  mb: 2,
                  '& .MuiOutlinedInput-root': {
                    background: 'rgba(10, 14, 23, 0.5)',
                    fontSize: '0.9rem',
                  },
                }}
              />

              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 1,
                }}
              >
                <Typography variant="caption" color="text.secondary" sx={{ flex: '1 1 240px', minWidth: 0 }}>
                  L'IA analysera votre texte et créera des nœuds
                </Typography>
                <Button
                  variant="contained"
                  onClick={handleSubmit}
                  disabled={!text.trim() || isProcessing}
                  startIcon={
                    isProcessing ? (
                      <CircularProgress size={18} color="inherit" />
                    ) : (
                      <AIIcon />
                    )
                  }
                  sx={{ minWidth: 120, flexShrink: 0 }}
                >
                  {isProcessing ? 'Analyse...' : 'Générer'}
                </Button>
              </Box>

              {/* Bouton de réorganisation IA */}
              {nodes.length > 1 && (
                <>
                  <Divider sx={{ my: 2, borderColor: 'rgba(0, 217, 255, 0.1)' }} />
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: 1,
                    }}
                  >
                    <Box>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        Réorganiser avec l'IA
                      </Typography>
                      <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.7rem' }}>
                        Fusionne les doublons, optimise la hiérarchie
                      </Typography>
                    </Box>
                    <Tooltip title="Réorganiser le mindmap avec l'IA">
                      <span>
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={handleReorganize}
                          disabled={isProcessing || nodes.length === 0}
                          startIcon={<ReorganizeIcon />}
                          sx={{
                            borderColor: 'rgba(139, 92, 246, 0.5)',
                            color: '#8B5CF6',
                            flexShrink: 0,
                            '&:hover': {
                            borderColor: '#8B5CF6',
                            backgroundColor: 'rgba(139, 92, 246, 0.1)',
                          },
                        }}
                      >
                        Optimiser
                      </Button>
                      </span>
                    </Tooltip>
                  </Box>
                </>
              )}
            </Box>
          </Collapse>
        </Box>
      </motion.div>

      {/* Processing Overlay */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Box
              sx={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(10, 14, 23, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 5,
                pointerEvents: 'none',
              }}
            >
              <Box
                sx={{
                  textAlign: 'center',
                  p: 4,
                  borderRadius: '20px',
                  background: 'rgba(18, 24, 43, 0.95)',
                  border: '1px solid rgba(0, 217, 255, 0.3)',
                }}
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                >
                  <AIIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                </motion.div>
                <Typography variant="h6">Analyse en cours...</Typography>
                <Typography variant="body2" color="text.secondary">
                  L'IA structure vos idées
                </Typography>
              </Box>
            </Box>
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  );
};

export default TextInput;

import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Chip,
} from '@mui/material';
import {
  AutoAwesome as AutoAwesomeIcon,
  Speed as SpeedIcon,
  Bolt as BoltIcon,
  AccountTree as AccountTreeIcon,
  SmartToy as SmartToyIcon,
  ArrowForward as ArrowForwardIcon,
  Psychology as PsychologyIcon,
  GppGood as GppGoodIcon,
} from '@mui/icons-material';
import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useLocation } from 'react-router-dom';
import HeroMindmapIllustration from './HeroMindmapIllustration';

const Landing = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const sc = document.getElementById('scroll-container');
    if (location.hash === '#features') {
      const t = window.setTimeout(() => {
        document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
      }, 80);
      return () => window.clearTimeout(t);
    }
    sc?.scrollTo({ top: 0, behavior: 'instant' });
  }, [location.hash, location.key]);

  const heroHighlights = [
    {
      icon: <PsychologyIcon sx={{ fontSize: 22 }} />,
      title: 'Intelligent',
      description: "L'IA structure, relie et enrichit vos idées",
    },
    {
      icon: <BoltIcon sx={{ fontSize: 22 }} />,
      title: 'Opérationnel',
      description: 'Chaque nœud devient une action déclenchable',
    },
    {
      icon: <GppGoodIcon sx={{ fontSize: 22 }} />,
      title: 'Maîtrisé',
      description: 'Vos données restent sous votre contrôle',
    },
  ];

  const features = [
    {
      icon: <AccountTreeIcon sx={{ fontSize: 32 }} />,
      title: 'Mindmap Intelligent',
      description: 'Organisez vos idées visuellement. L\'IA structure automatiquement vos pensées en un mindmap interactif.',
      color: '#00D9FF',
    },
    {
      icon: <SmartToyIcon sx={{ fontSize: 32 }} />,
      title: 'IA Conversationnelle',
      description: 'Postez un texte, l\'IA l\'analyse et crée automatiquement des nœuds et sous-nœuds structurés.',
      color: '#FF6B9D',
    },
    {
      icon: <BoltIcon sx={{ fontSize: 32 }} />,
      title: 'Triggers & Actions',
      description: 'Déclenchez des actions automatisées sur chaque nœud. Intégrez vos outils favoris.',
      color: '#4ADE80',
    },
    {
      icon: <SpeedIcon sx={{ fontSize: 32 }} />,
      title: 'Productivité Maximale',
      description: 'Gagnez du temps avec des workflows intelligents qui s\'adaptent à votre façon de travailler.',
      color: '#FBBF24',
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <Box sx={{ overflow: 'hidden' }}>
      {/* Hero Section */}
      <Box
        id="hero"
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          position: 'relative',
          pt: { xs: 8, md: 0 },
        }}
      >
        {/* Background Effects */}
        <Box
          sx={{
            position: 'absolute',
            top: '10%',
            left: '5%',
            width: 600,
            height: 600,
            borderRadius: '50%',
            backgroundColor: 'rgba(0, 217, 255, 0.05)',
            filter: 'blur(60px)',
            pointerEvents: 'none',
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: '10%',
            right: '10%',
            width: 500,
            height: 500,
            borderRadius: '50%',
            backgroundColor: 'rgba(255, 107, 157, 0.03)',
            filter: 'blur(60px)',
            pointerEvents: 'none',
          }}
        />

        <Container maxWidth="lg" sx={{ position: 'relative' }}>
          {/* Image — positionnée en absolu sur desktop pour couvrir toute la hauteur */}
          <Box
            sx={{
              display: { xs: 'none', lg: 'block' },
              position: 'absolute',
              top: '-5%',
              bottom: '-5%',
              right: 0,
              width: '55%',
              pointerEvents: 'none',
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              style={{ width: '100%', height: '100%' }}
            >
              <HeroMindmapIllustration />
            </motion.div>
          </Box>

          <Box sx={{ maxWidth: { lg: '45%' }, position: 'relative', zIndex: 1 }}>
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7 }}
            >
                <Chip
                  icon={<AutoAwesomeIcon sx={{ fontSize: 16, color: '#00D9FF !important' }} />}
                  label="Propulsé par l'IA"
                  sx={{
                    mb: 3,
                    background: 'rgba(0, 217, 255, 0.1)',
                    border: '1px solid rgba(0, 217, 255, 0.3)',
                    color: '#00D9FF',
                    fontWeight: 600,
                    '& .MuiChip-icon': { color: '#00D9FF' },
                  }}
                />
                <Typography
                  variant="h1"
                  sx={{
                    fontSize: { xs: '2.5rem', sm: '3.5rem', md: '4rem' },
                    lineHeight: 1.1,
                    mb: 3,
                  }}
                >
                  Votre cerveau,{' '}
                  <Box
                    component="span"
                    sx={{
                      color: '#00D9FF',
                    }}
                  >
                    augmenté par l'IA
                  </Box>
                </Typography>
                <Typography
                  variant="h5"
                  color="text.secondary"
                  sx={{ mb: 4, fontWeight: 400, lineHeight: 1.6 }}
                >
                  Transformez vos idées en actions automatisées. MindMapCompanion organise 
                  vos pensées en mindmaps intelligents et déclenche des workflows 
                  puissants sur chaque nœud.
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Button
                    variant="contained"
                    size="large"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => navigate('/login')}
                    sx={{ px: 4, py: 1.5 }}
                  >
                    Démarrer
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                    sx={{ px: 4, py: 1.5 }}
                  >
                    Découvrir
                  </Button>
                </Box>
                <Grid container spacing={2} sx={{ mt: { xs: 3, sm: 4 }, maxWidth: 560 }}>
                  {heroHighlights.map((item) => (
                    <Grid key={item.title} size={{ xs: 12, sm: 4 }}>
                      <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                        <Box
                          sx={{
                            flexShrink: 0,
                            width: 40,
                            height: 40,
                            borderRadius: '50%',
                            backgroundColor: 'rgba(0, 217, 255, 0.12)',
                            border: '1px solid rgba(0, 217, 255, 0.25)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#00D9FF',
                          }}
                        >
                          {item.icon}
                        </Box>
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, lineHeight: 1.3, mb: 0.25 }}>
                            {item.title}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8125rem', lineHeight: 1.5 }}>
                            {item.description}
                          </Typography>
                        </Box>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </motion.div>
            </Box>

          {/* Image mobile / tablette (flux normal) */}
          <Box sx={{ display: { xs: 'block', lg: 'none' }, mt: 4 }}>
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, delay: 0.2 }}
            >
              <Box sx={{ height: { xs: 320, sm: 400, md: 480 } }}>
                <HeroMindmapIllustration />
              </Box>
            </motion.div>
          </Box>
        </Container>
      </Box>

      {/* Features Section */}
      <Box id="features" sx={{ py: { xs: 10, md: 15 } }}>
        <Container maxWidth="lg">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-100px' }}
          >
            <motion.div variants={itemVariants}>
              <Typography
                variant="h2"
                align="center"
                sx={{
                  fontSize: { xs: '2rem', md: '3rem' },
                  mb: 2,
                }}
              >
                Fonctionnalités{' '}
                <Box
                  component="span"
                  sx={{
                    color: '#00D9FF',
                  }}
                >
                  puissantes
                </Box>
              </Typography>
              <Typography
                variant="h6"
                color="text.secondary"
                align="center"
                sx={{ mb: 8, maxWidth: 600, mx: 'auto' }}
              >
                Tout ce dont vous avez besoin pour transformer vos idées en réalité
              </Typography>
            </motion.div>

            <Grid container spacing={4}>
              {features.map((feature, index) => (
                <Grid size={{ xs: 12, sm: 6, lg: 3 }} key={index}>
                  <motion.div variants={itemVariants}>
                    <Card
                      sx={{
                        height: '100%',
                        transition: 'all 0.3s ease',
                        cursor: 'pointer',
                        '&:hover': {
                          transform: 'translateY(-8px)',
                          boxShadow: `0 20px 40px rgba(${feature.color === '#00D9FF' ? '0, 217, 255' : feature.color === '#FF6B9D' ? '255, 107, 157' : feature.color === '#4ADE80' ? '74, 222, 128' : '251, 191, 36'}, 0.2)`,
                          borderColor: feature.color,
                        },
                      }}
                    >
                      <CardContent sx={{ p: 4 }}>
                        <Box
                          sx={{
                            width: 60,
                            height: 60,
                            borderRadius: '16px',
                            background: `${feature.color}15`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            mb: 3,
                            color: feature.color,
                          }}
                        >
                          {feature.icon}
                        </Box>
                        <Typography variant="h5" sx={{ mb: 2, fontWeight: 600 }}>
                          {feature.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                          {feature.description}
                        </Typography>
                      </CardContent>
                    </Card>
                  </motion.div>
                </Grid>
              ))}
            </Grid>
          </motion.div>
        </Container>
      </Box>

      {/* CTA Section */}
      <Box sx={{ py: { xs: 10, md: 15 } }}>
        <Container maxWidth="md">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <Card
              sx={{
                p: { xs: 4, md: 8 },
                textAlign: 'center',
                backgroundColor: 'rgba(0, 217, 255, 0.08)',
                border: '1px solid rgba(0, 217, 255, 0.2)',
              }}
            >
              <Typography variant="h3" sx={{ mb: 2, fontSize: { xs: '1.75rem', md: '2.5rem' } }}>
                Prêt à booster votre productivité ?
              </Typography>
              <Typography
                variant="h6"
                color="text.secondary"
                sx={{ mb: 4, maxWidth: 500, mx: 'auto' }}
              >
                Projet open source sous licence MIT : installez-le, essayez-le et
                adaptez-le à votre façon d&apos;organiser vos idées et vos actions.
              </Typography>
              <Button
                variant="contained"
                size="large"
                endIcon={<ArrowForwardIcon />}
                onClick={() => navigate('/login')}
                sx={{ px: 5, py: 1.5 }}
              >
                Commencer maintenant
              </Button>
            </Card>
          </motion.div>
        </Container>
      </Box>
    </Box>
  );
};

export default Landing;

import { Box, Container, Typography, IconButton, Link } from '@mui/material';
import { GitHub as GitHubIcon, AutoAwesome as AutoAwesomeIcon } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { motion } from 'framer-motion';

const REPO_URL = 'https://github.com/MaillardBenjamin/MindMapCompanion';
const LICENSE_URL = `${REPO_URL}/blob/main/LICENSE`;

const Footer = () => {
  return (
    <Box
      component="footer"
      sx={{
        py: 6,
        backgroundColor: '#0A0E17',
        borderTop: '1px solid rgba(0, 217, 255, 0.1)',
      }}
    >
      <Container maxWidth="lg">
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', md: 'row' },
            gap: { xs: 4, md: 6 },
            alignItems: { xs: 'flex-start', md: 'flex-start' },
            justifyContent: 'space-between',
          }}
        >
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            viewport={{ once: true }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '10px',
                  backgroundColor: '#00D9FF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <AutoAwesomeIcon sx={{ color: '#0A0E17', fontSize: 22 }} />
              </Box>
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 800,
                  backgroundColor: '#00D9FF',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                MindMapCompanion
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 360, mb: 2 }}>
              Projet open source pour organiser vos idées en mindmaps et brancher des automatisations. Libre d&apos;utilisation, de modification et de redistribution sous licence MIT.
            </Typography>
            <IconButton
              component="a"
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Dépôt GitHub"
              sx={{
                color: 'text.secondary',
                border: '1px solid rgba(139, 149, 168, 0.2)',
                borderRadius: '10px',
                '&:hover': {
                  color: 'primary.main',
                  borderColor: 'primary.main',
                  background: 'rgba(0, 217, 255, 0.1)',
                },
              }}
            >
              <GitHubIcon fontSize="small" />
            </IconButton>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
            viewport={{ once: true }}
          >
            <Typography
              variant="subtitle2"
              sx={{
                color: 'text.primary',
                fontWeight: 600,
                mb: 2,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                fontSize: '0.75rem',
              }}
            >
              Projet
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
              <Link
                component={RouterLink}
                to="/#features"
                underline="none"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.9rem',
                  transition: 'all 0.2s ease',
                  '&:hover': { color: 'primary.main', transform: 'translateX(4px)' },
                }}
              >
                Fonctionnalités
              </Link>
              <Link
                component={RouterLink}
                to="/about"
                underline="none"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.9rem',
                  transition: 'all 0.2s ease',
                  '&:hover': { color: 'primary.main', transform: 'translateX(4px)' },
                }}
              >
                À propos
              </Link>
              <Link
                href={REPO_URL}
                underline="none"
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.9rem',
                  transition: 'all 0.2s ease',
                  '&:hover': { color: 'primary.main', transform: 'translateX(4px)' },
                }}
              >
                Code source (GitHub)
              </Link>
              <Link
                href={LICENSE_URL}
                underline="none"
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  color: 'text.secondary',
                  fontSize: '0.9rem',
                  transition: 'all 0.2s ease',
                  '&:hover': { color: 'primary.main', transform: 'translateX(4px)' },
                }}
              >
                Licence MIT
              </Link>
            </Box>
          </motion.div>
        </Box>

        <Box
          sx={{
            mt: 6,
            pt: 3,
            borderTop: '1px solid rgba(139, 149, 168, 0.1)',
          }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
            Sous licence{' '}
            <Link href={LICENSE_URL} target="_blank" rel="noopener noreferrer" color="inherit" sx={{ fontWeight: 600 }}>
              MIT
            </Link>
            . Copyright © 2026 Benjamin Maillard.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default Footer;

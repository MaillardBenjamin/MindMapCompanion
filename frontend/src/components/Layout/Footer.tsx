import { Box, Container, Typography, Grid, IconButton, Link } from '@mui/material';
import {
  GitHub as GitHubIcon,
  LinkedIn as LinkedInIcon,
  Twitter as TwitterIcon,
  AutoAwesome as AutoAwesomeIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const Footer = () => {
  const footerLinks = {
    product: [
      { label: 'Fonctionnalités', href: '/#features' },
      { label: 'Mindmap IA', href: '/#mindmap' },
      { label: 'Automatisations', href: '/#automation' },
    ],
    resources: [
      { label: 'Documentation', href: '/docs' },
      { label: 'API', href: '/api' },
      { label: 'Support', href: '/support' },
    ],
    company: [
      { label: 'À propos', href: '/about' },
      { label: 'Contact', href: '/contact' },
      { label: 'Mentions légales', href: '/legal' },
    ],
  };

  return (
    <Box
      component="footer"
      sx={{
        py: 8,
        backgroundColor: '#0A0E17',
        borderTop: '1px solid rgba(0, 217, 255, 0.1)',
      }}
    >
      <Container maxWidth="lg">
        <Grid container spacing={6}>
          <Grid size={{ xs: 12, md: 4 }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
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
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 280 }}>
                Votre assistant personnel intelligent pour organiser vos idées, 
                automatiser vos tâches et libérer votre créativité.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                {[GitHubIcon, LinkedInIcon, TwitterIcon].map((Icon, index) => (
                  <IconButton
                    key={index}
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
                    <Icon fontSize="small" />
                  </IconButton>
                ))}
              </Box>
            </motion.div>
          </Grid>

          {Object.entries(footerLinks).map(([category, links], categoryIndex) => (
            <Grid size={{ xs: 6, sm: 4, md: 2 }} key={category}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: categoryIndex * 0.1 }}
                viewport={{ once: true }}
              >
                <Typography
                  variant="subtitle2"
                  sx={{
                    color: 'text.primary',
                    fontWeight: 600,
                    mb: 2.5,
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    fontSize: '0.75rem',
                  }}
                >
                  {category === 'product' ? 'Produit' : category === 'resources' ? 'Ressources' : 'Entreprise'}
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {links.map((link) => (
                    <Link
                      key={link.label}
                      href={link.href}
                      underline="none"
                      sx={{
                        color: 'text.secondary',
                        fontSize: '0.9rem',
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          color: 'primary.main',
                          transform: 'translateX(4px)',
                        },
                      }}
                    >
                      {link.label}
                    </Link>
                  ))}
                </Box>
              </motion.div>
            </Grid>
          ))}
        </Grid>

        <Box
          sx={{
            mt: 8,
            pt: 4,
            borderTop: '1px solid rgba(139, 149, 168, 0.1)',
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 2,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            © 2026 MindMapCompanion. Tous droits réservés.
          </Typography>
          <Box sx={{ display: 'flex', gap: 3 }}>
            <Link href="/privacy" underline="none" sx={{ color: 'text.secondary', fontSize: '0.875rem', '&:hover': { color: 'primary.main' } }}>
              Confidentialité
            </Link>
            <Link href="/terms" underline="none" sx={{ color: 'text.secondary', fontSize: '0.875rem', '&:hover': { color: 'primary.main' } }}>
              Conditions
            </Link>
          </Box>
        </Box>
      </Container>
    </Box>
  );
};

export default Footer;

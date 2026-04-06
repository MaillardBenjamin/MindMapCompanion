import { useEffect } from 'react';
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
  OpenInNew as OpenInNewIcon,
  LinkedIn as LinkedInIcon,
  Language as WebIcon,
  Psychology as PsychologyIcon,
  AccountTree as AccountTreeIcon,
  SmartToy as SmartToyIcon,
  Bolt as BoltIcon,
  AutoAwesome as AutoAwesomeIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const CYAN = '#00D9FF';
const PINK = '#FF6B9D';
const GREEN = '#4ADE80';

const projectFeatures = [
  {
    icon: <AccountTreeIcon sx={{ fontSize: 28 }} />,
    title: 'Penser en arbre',
    desc: 'Votre cerveau ne fonctionne pas en liste. MindMapCompanion vous laisse organiser vos idées comme elles viennent, en branches et en connexions.',
    color: CYAN,
  },
  {
    icon: <SmartToyIcon sx={{ fontSize: 28 }} />,
    title: 'Des agents, pas des boutons',
    desc: 'Chaque nœud peut invoquer un agent IA spécialisé : résumé, audit, recherche. L\'IA travaille pour vous, au bon endroit.',
    color: PINK,
  },
  {
    icon: <BoltIcon sx={{ fontSize: 28 }} />,
    title: 'De l\'idée à l\'action',
    desc: 'Un trigger sur un nœud, et c\'est parti : notifications, monitoring, workflows. Vos idées ne restent plus au stade de l\'intention.',
    color: GREEN,
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const About = () => {
  useEffect(() => {
    document.getElementById('scroll-container')?.scrollTo({ top: 0, behavior: 'instant' });
  }, []);

  return (
    <Box sx={{ pb: { xs: 8, md: 14 } }}>

      {/* ─── Hero personnel ─── */}
      <Box
        sx={{
          position: 'relative',
          pt: { xs: 4, md: 8 },
          pb: { xs: 6, md: 10 },
          '&::before': {
            content: '""',
            position: 'absolute',
            top: '-15%',
            right: '-8%',
            width: 550,
            height: 550,
            borderRadius: '50%',
            background: 'rgba(0,217,255,0.04)',
            filter: 'blur(80px)',
            pointerEvents: 'none',
          },
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={{ xs: 4, md: 6 }} alignItems="center">
            {/* Photo */}
            <Grid size={{ xs: 12, md: 5 }}>
              <motion.div
                initial={{ opacity: 0, scale: 0.94 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.55 }}
              >
                <Box sx={{ position: 'relative', maxWidth: 380, mx: { xs: 'auto', md: 0 } }}>
                  <Box
                    component="img"
                    src="/benjamin-maillard-about.png"
                    alt="Benjamin Maillard"
                    sx={{
                      width: '100%',
                      display: 'block',
                      borderRadius: 3,
                      border: '1px solid rgba(0,217,255,0.22)',
                      boxShadow: '0 28px 72px rgba(0,0,0,0.4)',
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: -16,
                      right: -16,
                      width: 72,
                      height: 72,
                      borderRadius: '50%',
                      background: `linear-gradient(135deg, ${CYAN}, ${PINK})`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 0 28px rgba(0,217,255,0.35)',
                    }}
                  >
                    <PsychologyIcon sx={{ fontSize: 34, color: '#0A0E17' }} />
                  </Box>
                </Box>
              </motion.div>
            </Grid>

            {/* Texte narratif */}
            <Grid size={{ xs: 12, md: 7 }}>
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.55, delay: 0.12 }}
              >
                <Chip
                  icon={<AutoAwesomeIcon sx={{ fontSize: 16, color: `${CYAN} !important` }} />}
                  label="Créateur de MindMapCompanion"
                  sx={{
                    mb: 2.5,
                    background: 'rgba(0,217,255,0.1)',
                    border: '1px solid rgba(0,217,255,0.3)',
                    color: CYAN,
                    fontWeight: 600,
                    '& .MuiChip-icon': { color: CYAN },
                  }}
                />
                <Typography
                  variant="h2"
                  sx={{
                    fontSize: { xs: '2rem', sm: '2.5rem', md: '3rem' },
                    fontWeight: 800,
                    lineHeight: 1.15,
                    mb: 3,
                  }}
                >
                  Benjamin{' '}
                  <Box component="span" sx={{ color: CYAN }}>Maillard</Box>
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ mb: 2.5, lineHeight: 1.85, fontSize: '1.05rem' }}>
                  Passionné depuis toujours par l'informatique et l'intelligence artificielle,
                  j'ai grandi avec l'envie de comprendre comment les machines peuvent amplifier
                  la pensée humaine. Des premiers programmes en BASIC sur un Thomson MO5 jusqu'aux
                  architectures multi-agents d'aujourd'hui, le fil rouge est resté le même :
                  transformer la technologie en quelque chose d'utile, de concret et, si possible,
                  d'un peu magique.
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ mb: 2.5, lineHeight: 1.85, fontSize: '1.05rem' }}>
                  Dans la vie professionnelle, je dirige les systèmes d'information et les
                  projets billettiques chez{' '}
                  <Box component="span" sx={{ color: CYAN, fontWeight: 600 }}>Comutitres</Box>{' '}
                  (le pass Navigo). Plus de vingt ans à piloter des programmes de transformation
                  numérique m'ont appris une chose : les meilleures idées émergent rarement de
                  façon linéaire. Elles se ramifient, se connectent, appellent des actions -- et
                  la plupart des outils ne savent pas suivre ce rythme.
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ mb: 4, lineHeight: 1.85, fontSize: '1.05rem' }}>
                  C'est pour ça que j'ai créé{' '}
                  <Box component="span" sx={{ fontWeight: 700, color: '#E8EDF5' }}>MindMapCompanion</Box>.
                  Un terrain de jeu où mes deux passions se rencontrent : le mind mapping comme
                  façon de penser, et l'IA comme moteur d'action. Un projet personnel, construit
                  le soir et le week-end, qui me permet d'explorer tout ce qui me fascine --
                  agents autonomes, workflows intelligents, interfaces réactives -- et de le
                  partager.
                </Typography>

                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<WebIcon />}
                    endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
                    href="https://benjamin-maillard.fr/"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    benjamin-maillard.fr
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    startIcon={<LinkedInIcon />}
                    endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
                    href="https://www.linkedin.com/in/benjaminmaillard"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    LinkedIn
                  </Button>
                </Box>
              </motion.div>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* ─── Pourquoi MindMapCompanion ─── */}
      <Box sx={{ py: { xs: 8, md: 12 } }}>
        <Container maxWidth="md">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true, margin: '-60px' }}
          >
            <Typography
              variant="h3"
              align="center"
              sx={{ fontSize: { xs: '1.75rem', md: '2.25rem' }, fontWeight: 800, mb: 3 }}
            >
              Pourquoi{' '}
              <Box component="span" sx={{ color: CYAN }}>ce projet</Box> ?
            </Typography>
            <Typography
              variant="body1"
              align="center"
              color="text.secondary"
              sx={{ lineHeight: 1.85, fontSize: '1.05rem', mb: 2 }}
            >
              J'ai toujours fonctionné en cartes mentales -- sur papier, sur tableau blanc,
              dans ma tête. Quand l'IA générative a commencé à devenir vraiment utilisable, j'ai
              vu l'occasion de fusionner les deux : un espace où chaque branche de votre
              réflexion peut déclencher une action intelligente, sans quitter votre flux de
              pensée.
            </Typography>
            <Typography
              variant="body1"
              align="center"
              color="text.secondary"
              sx={{ lineHeight: 1.85, fontSize: '1.05rem' }}
            >
              MindMapCompanion n'est pas un produit d'entreprise aseptisé. C'est un projet de
              passion, un laboratoire où j'expérimente les architectures agentic AI, les
              workflows event-driven et les interfaces qui respectent la façon dont on pense
              vraiment. Si ça vous parle, vous êtes au bon endroit.
            </Typography>
          </motion.div>
        </Container>
      </Box>

      {/* ─── Trois piliers ─── */}
      <Box sx={{ py: { xs: 6, md: 10 } }}>
        <Container maxWidth="lg">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-80px' }}
          >
            <Grid container spacing={4}>
              {projectFeatures.map((feat) => (
                <Grid size={{ xs: 12, sm: 4 }} key={feat.title}>
                  <motion.div variants={itemVariants}>
                    <Card
                      sx={{
                        height: '100%',
                        transition: 'all 0.3s',
                        '&:hover': {
                          transform: 'translateY(-6px)',
                          borderColor: feat.color,
                          boxShadow: `0 16px 40px ${feat.color}20`,
                        },
                      }}
                    >
                      <CardContent sx={{ p: 4 }}>
                        <Box
                          sx={{
                            width: 54,
                            height: 54,
                            borderRadius: '14px',
                            background: `${feat.color}14`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            mb: 2.5,
                            color: feat.color,
                          }}
                        >
                          {feat.icon}
                        </Box>
                        <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                          {feat.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.75 }}>
                          {feat.desc}
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

      {/* ─── CTA ─── */}
      <Box sx={{ pt: { xs: 4, md: 6 } }}>
        <Container maxWidth="md">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
          >
            <Card
              sx={{
                p: { xs: 4, md: 6 },
                textAlign: 'center',
                background: 'rgba(0,217,255,0.06)',
                border: '1px solid rgba(0,217,255,0.18)',
              }}
            >
              <Typography
                variant="h4"
                sx={{ fontWeight: 800, mb: 1.5, fontSize: { xs: '1.4rem', md: '1.85rem' } }}
              >
                Envie de creuser ?
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 520, mx: 'auto', lineHeight: 1.7 }}>
                Articles sur l'Agentic AI, retours d'expérience terrain, architectures web
                modernes -- tout est sur le site personnel.
              </Typography>
              <Box sx={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 2 }}>
                <Button
                  variant="contained"
                  size="large"
                  endIcon={<OpenInNewIcon />}
                  href="https://benjamin-maillard.fr/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Voir le site
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  endIcon={<OpenInNewIcon />}
                  href="https://www.linkedin.com/in/benjaminmaillard"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Profil LinkedIn
                </Button>
              </Box>
            </Card>
          </motion.div>
        </Container>
      </Box>
    </Box>
  );
};

export default About;

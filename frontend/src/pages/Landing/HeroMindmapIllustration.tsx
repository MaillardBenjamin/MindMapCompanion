import { Box } from '@mui/material';

const HeroMindmapIllustration = () => (
  <Box
    sx={{
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}
  >
    <Box
      component="img"
      src="/hero-mindmap.png"
      alt="Réseau cognitif : cerveau lumineux au centre, branches colorées vers des nœuds thématiques (contexte, idées, action, données, triggers)."
      sx={{
        width: '100%',
        height: '100%',
        objectFit: 'contain',
        objectPosition: 'center',
        filter: [
          'drop-shadow(0 10px 32px rgba(0, 0, 0, 0.5))',
          'drop-shadow(0 0 28px rgba(0, 217, 255, 0.18))',
        ].join(' '),
        userSelect: 'none',
        pointerEvents: 'none',
      }}
      draggable={false}
    />
  </Box>
);

export default HeroMindmapIllustration;

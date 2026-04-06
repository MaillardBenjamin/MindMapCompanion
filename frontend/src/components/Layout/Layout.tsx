import { Box } from '@mui/material';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';

interface LayoutProps {
  showFooter?: boolean;
}

const Layout = ({ showFooter = true }: LayoutProps) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />
      <Box
        id="scroll-container"
        sx={{
          flexGrow: 1,
          overflow: 'auto',
        }}
      >
        <Box
          component="main"
          sx={{ pt: { xs: 8, md: 10 } }}
        >
          <Outlet />
        </Box>
        {showFooter && <Footer />}
      </Box>
    </Box>
  );
};

export default Layout;

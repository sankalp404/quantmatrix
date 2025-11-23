import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ChakraProvider, extendTheme } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { AccountProvider } from './context/AccountContext';
import { AuthProvider } from './context/AuthContext';

// Layout components
import DashboardLayout from './components/layout/DashboardLayout';

// Page components
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import PortfolioCategories from './pages/PortfolioCategories';
import Stocks from './pages/Stocks';
import OptionsPortfolio from './pages/OptionsPortfolio';
import TaxLots from './pages/TaxLots';
import DividendsCalendar from './pages/DividendsCalendar';
import Transactions from './pages/Transactions';
import MarginAnalysis from './pages/MarginAnalysis';
import Analytics from './pages/Analytics';
import Strategies from './pages/Strategies';
import StrategiesManager from './pages/StrategiesManager';
import Notifications from './pages/Notifications';
import SettingsShell from './pages/SettingsShell';
import Settings from './pages/Settings';
import PortfolioWorkspace from './pages/PortfolioWorkspace';
import Login from './pages/Login';
import Register from './pages/Register';
import RequireAuth from './components/auth/RequireAuth';
import { Box, Heading, Text } from '@chakra-ui/react';

// Theme configuration inspired by Snowball Analytics
const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      50: '#E6F3FF',
      100: '#BAE3FF',
      200: '#7CC4FA',
      300: '#47A3F3',
      400: '#2186EB',
      500: '#0967D2',
      600: '#0552B5',
      700: '#03449E',
      800: '#01337D',
      900: '#002159',
    },
    accent: {
      yellow: {
        50: '#FFF9E6',
        100: '#FFEEB3',
        200: '#FFE180',
        300: '#FFD24D',
        400: '#FFC21A',
        500: '#E0A800',
        600: '#B38300',
        700: '#856100',
        800: '#594200',
        900: '#2E2200'
      }
    },
    gray: {
      50: '#F7FAFC',
      100: '#EDF2F7',
      200: '#E2E8F0',
      300: '#CBD5E0',
      400: '#A0AEC0',
      500: '#718096',
      600: '#4A5568',
      700: '#2D3748',
      800: '#1A202C',
      900: '#171923',
    }
  },
  fonts: {
    heading: `'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'`,
    body: `'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'`,
  },
  styles: {
    global: (props: any) => ({
      body: {
        bg: props.colorMode === 'dark' ? 'gray.900' : 'gray.50',
        color: props.colorMode === 'dark' ? 'white' : 'gray.800',
      },
    }),
  },
  components: {
    Card: {
      baseStyle: {
        container: {
          borderRadius: 'lg',
          boxShadow: 'sm',
          bg: 'gray.800',
          border: '1px solid',
          borderColor: 'gray.700',
        }
      }
    },
    Button: {
      defaultProps: {
        colorScheme: 'brand',
      },
    },
  },
});

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 5, // 5 minutes
    },
  },
});

const BoxPlaceholder: React.FC<{ title: string }> = ({ title }) => (
  <Box p={6}>
    <Heading size="md" mb={2}>{title}</Heading>
    <Text color="gray.500">This section is coming soon.</Text>
  </Box>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>
        <AuthProvider>
          <AccountProvider>
            <Router>
              <Routes>
                <Route path="/" element={<RequireAuth><DashboardLayout /></RequireAuth>}>
                  <Route index element={<Dashboard />} />
                  <Route path="portfolio" element={<Portfolio />} />
                  <Route path="portfolio-categories" element={<PortfolioCategories />} />
                  <Route path="stocks" element={<Stocks />} />
                  <Route path="options-portfolio" element={<OptionsPortfolio />} />
                  <Route path="tax-lots" element={<TaxLots />} />
                  <Route path="dividends" element={<DividendsCalendar />} />
                  <Route path="transactions" element={<Transactions />} />
                  <Route path="margin" element={<MarginAnalysis />} />
                  <Route path="analytics" element={<Analytics />} />
                  <Route path="strategies" element={<Strategies />} />
                  <Route path="strategies-manager" element={<StrategiesManager />} />
                  <Route path="notifications" element={<Notifications />} />
                  <Route path="settings" element={<SettingsShell />}>
                    <Route index element={<Settings />} />
                    <Route path="profile" element={<BoxPlaceholder title="Profile" />} />
                    <Route path="preferences" element={<BoxPlaceholder title="Preferences" />} />
                    <Route path="notifications" element={<BoxPlaceholder title="Notifications" />} />
                    <Route path="security" element={<BoxPlaceholder title="Security" />} />
                    <Route path="brokerages" element={<Settings />} />
                  </Route>
                  <Route path="workspace" element={<PortfolioWorkspace />} />
                </Route>
              </Routes>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
              </Routes>
              <Toaster
                position="top-right"
                toastOptions={{
                  style: {
                    background: '#2D3748',
                    color: '#fff',
                    border: '1px solid #4A5568',
                  },
                }}
              />
            </Router>
          </AccountProvider>
        </AuthProvider>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

export default App; 
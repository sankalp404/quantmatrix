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
import AdminDashboard from './pages/AdminDashboard';
import AdminJobs from './pages/AdminJobs';
import AdminSchedules from './pages/AdminSchedules';
import AdminCoverage from './pages/AdminCoverage';
import AdminTracked from './pages/AdminTracked';
import AdminRunbook from './pages/AdminRunbook';

const surfacePalette = {
  dark: {
    base: '#111B2B',
    panel: '#182233',
    card: '#1C2737',
    raised: '#24344B',
    border: '#2F4461',
    muted: '#A2B9D6',
  },
  light: {
    base: '#F4F6FB',
    panel: '#ECF1FA',
    card: '#E2E9F6',
    raised: '#D6E0F2',
    border: '#C5D2E7',
    muted: '#4A5B74',
  },
};

const surfaceTokens = {
  'surface.base': { default: surfacePalette.light.base, _dark: surfacePalette.dark.base },
  'surface.panel': { default: surfacePalette.light.panel, _dark: surfacePalette.dark.panel },
  'surface.card': { default: surfacePalette.light.card, _dark: surfacePalette.dark.card },
  'surface.raised': { default: surfacePalette.light.raised, _dark: surfacePalette.dark.raised },
  'surface.border': { default: surfacePalette.light.border, _dark: surfacePalette.dark.border },
  'text.muted': { default: surfacePalette.light.muted, _dark: surfacePalette.dark.muted },
};

const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: true,
  },
  colors: {
    brand: {
      50: '#E6F1FF',
      100: '#C2DBFF',
      200: '#9AC4FF',
      300: '#73AAFF',
      400: '#4F91FF',
      500: '#2A79F0',
      600: '#1B5DC3',
      700: '#124397',
      800: '#0A2B6A',
      900: '#041840',
    },
    accent: {
      teal: '#5FD4F5',
      sand: '#EDBA72',
    },
    gray: {
      50: '#EAF0F8',
      100: '#D2DDEB',
      200: '#BAC9DD',
      300: '#A2B4CC',
      400: '#8A9FBA',
      500: '#7389A5',
      600: '#5C6E85',
      700: '#455165',
      800: '#2D3443',
      900: '#1A1E28',
    },
  },
  semanticTokens: {
    colors: surfaceTokens,
  },
  fonts: {
    heading: `'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'`,
    body: `'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'`,
  },
  styles: {
    global: {
      body: {
        bg: 'surface.base',
        color: 'gray.900',
        _dark: { color: 'gray.50' },
      },
      '*::selection': {
        background: 'rgba(79, 145, 255, 0.35)',
      },
    },
  },
  components: {
    Card: {
      baseStyle: {
        container: {
          borderRadius: 'xl',
          border: '1px solid',
          borderColor: 'surface.border',
          bg: 'surface.card',
          boxShadow: 'md',
          padding: 4,
        },
      },
    },
    Heading: {
      baseStyle: {
        color: 'gray.900',
        letterSpacing: '-0.01em',
        _dark: {
          color: 'gray.50',
        },
      },
    },
    Button: {
      baseStyle: {
        borderRadius: 'lg',
        fontWeight: 600,
      },
      variants: {
        solid: {
          bg: 'brand.500',
          color: 'white',
          _hover: {
            bg: 'brand.400',
          },
          _active: {
            bg: 'brand.600',
          },
        },
        outline: {
          borderColor: 'surface.border',
          color: 'gray.100',
          _hover: {
            bg: 'surface.panel',
          },
        },
      },
      defaultProps: {
        colorScheme: 'brand',
      },
    },
    Tabs: {
      baseStyle: {
        tab: {
          fontWeight: 500,
        },
      },
      variants: {
        enclosed: {
          tab: {
            bg: 'transparent',
            borderBottom: '2px solid',
            borderColor: 'transparent',
            _selected: {
              color: 'brand.200',
              borderColor: 'brand.400',
            },
          },
          tabpanel: {
            bg: 'surface.panel',
            borderRadius: 'lg',
            border: '1px solid',
            borderColor: 'surface.border',
            marginTop: 2,
            padding: 4,
          },
        },
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
                    {/* Market Data (read-only) */}
                    <Route path="market/coverage" element={<AdminCoverage />} />
                    <Route path="market/tracked" element={<AdminTracked />} />
                    {/* Admin under Settings */}
                    <Route path="admin/dashboard" element={<AdminDashboard />} />
                    <Route path="admin/jobs" element={<AdminJobs />} />
                    <Route path="admin/schedules" element={<AdminSchedules />} />
                    <Route path="admin/runbook" element={<AdminRunbook />} />
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
                    background: surfacePalette.dark.panel,
                    color: '#F7F9FC',
                    border: `1px solid ${surfacePalette.dark.border}`,
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
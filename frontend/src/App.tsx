import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { AccountProvider } from './context/AccountContext';
import { AuthProvider } from './context/AuthContext';
import { ColorModeProvider } from './theme/colorMode';
import { system } from './theme/system';
import ErrorBoundary from './components/ErrorBoundary';

import RequireAuth from './components/auth/RequireAuth';

// Lazy-load routes so Chakra v3 migration can happen page-by-page
const DashboardLayout = React.lazy(() => import('./components/layout/DashboardLayout'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Portfolio = React.lazy(() => import('./pages/Portfolio'));
const PortfolioCategories = React.lazy(() => import('./pages/PortfolioCategories'));
const Stocks = React.lazy(() => import('./pages/Stocks'));
const OptionsPortfolio = React.lazy(() => import('./pages/OptionsPortfolio'));
const TaxLots = React.lazy(() => import('./pages/TaxLots'));
const DividendsCalendar = React.lazy(() => import('./pages/DividendsCalendar'));
const Transactions = React.lazy(() => import('./pages/Transactions'));
const MarginAnalysis = React.lazy(() => import('./pages/MarginAnalysis'));
const Analytics = React.lazy(() => import('./pages/Analytics'));
const Strategies = React.lazy(() => import('./pages/Strategies'));
const StrategiesManager = React.lazy(() => import('./pages/StrategiesManager'));
const Notifications = React.lazy(() => import('./pages/Notifications'));
const SettingsShell = React.lazy(() => import('./pages/SettingsShell'));
const Settings = React.lazy(() => import('./pages/Settings'));
const SettingsProfile = React.lazy(() => import('./pages/SettingsProfile'));
const SettingsPreferences = React.lazy(() => import('./pages/SettingsPreferences'));
const SettingsNotifications = React.lazy(() => import('./pages/SettingsNotifications'));
const SettingsSecurity = React.lazy(() => import('./pages/SettingsSecurity'));
const PortfolioWorkspace = React.lazy(() => import('./pages/PortfolioWorkspace'));
const Login = React.lazy(() => import('./pages/Login'));
const Register = React.lazy(() => import('./pages/Register'));
const AdminDashboard = React.lazy(() => import('./pages/AdminDashboard'));
const AdminJobs = React.lazy(() => import('./pages/AdminJobs'));
const AdminSchedules = React.lazy(() => import('./pages/AdminSchedules'));
const MarketCoverage = React.lazy(() => import('./pages/MarketCoverage'));
const MarketTracked = React.lazy(() => import('./pages/MarketTracked'));

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

const RouteFallback: React.FC = () => (
  <div style={{ padding: 16, fontFamily: 'system-ui' }}>Loading…</div>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ColorModeProvider>
        <ChakraProvider value={system}>
          <AuthProvider>
            <AccountProvider>
              <ErrorBoundary>
                <Router>
                  <Suspense fallback={<RouteFallback />}>
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
                          <Route index element={<Navigate to="profile" replace />} />
                          <Route path="profile" element={<SettingsProfile />} />
                          <Route path="preferences" element={<SettingsPreferences />} />
                          <Route path="notifications" element={<SettingsNotifications />} />
                          <Route path="brokerages" element={<Settings />} />
                          <Route path="security" element={<SettingsSecurity />} />
                          {/* Market Data (read-only) */}
                          <Route path="market/coverage" element={<MarketCoverage />} />
                          <Route path="market/tracked" element={<MarketTracked />} />
                          {/* Admin under Settings */}
                          <Route path="admin/dashboard" element={<AdminDashboard />} />
                          <Route path="admin/jobs" element={<AdminJobs />} />
                          <Route path="admin/schedules" element={<AdminSchedules />} />
                        </Route>
                        <Route path="workspace" element={<PortfolioWorkspace />} />
                      </Route>
                      <Route path="/login" element={<Login />} />
                      <Route path="/register" element={<Register />} />
                    </Routes>
                  </Suspense>
                  <Toaster
                    position="top-right"
                    toastOptions={{
                      style: {
                        background: 'var(--chakra-colors-bg-panel)',
                        color: 'var(--chakra-colors-fg-default)',
                        border: '1px solid var(--chakra-colors-border-subtle)',
                      },
                    }}
                  />
                </Router>
              </ErrorBoundary>
            </AccountProvider>
          </AuthProvider>
        </ChakraProvider>
      </ColorModeProvider>
    </QueryClientProvider>
  );
}

export default App; 
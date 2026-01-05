import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { render, screen } from '@testing-library/react';
import SettingsShell from '../../pages/SettingsShell';
import { system } from '../../theme/system';

vi.mock('../../context/AuthContext', async () => {
  return {
    useAuth: () => ({ user: { role: 'admin' } }),
  };
});

vi.mock('../../services/api', () => {
  return {
    default: {
      get: vi.fn().mockResolvedValue({ data: { meta: { exposed_to_all: true } } }),
    },
  };
});

describe('SettingsShell', () => {
  it('renders sidebar sections', () => {
    render(
      <ChakraProvider value={system}>
        <MemoryRouter initialEntries={['/settings']}>
          <SettingsShell />
        </MemoryRouter>
      </ChakraProvider>
    );
    // On small screens SettingsShell collapses to an icon rail, so links are aria-labels.
    expect(screen.getByRole('button', { name: /Profile/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Preferences/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Notifications/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Brokerages/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Security/i })).toBeInTheDocument();
  });
});





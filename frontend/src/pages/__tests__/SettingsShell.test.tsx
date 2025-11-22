import React from 'react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { render, screen } from '@testing-library/react';
import SettingsShell from '../../pages/SettingsShell';

describe('SettingsShell', () => {
  it('renders sidebar sections', () => {
    render(
      <ChakraProvider>
        <MemoryRouter initialEntries={['/settings']}>
          <SettingsShell />
        </MemoryRouter>
      </ChakraProvider>
    );
    expect(screen.getByText(/Profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Preferences/i)).toBeInTheDocument();
    expect(screen.getByText(/Notifications/i)).toBeInTheDocument();
    expect(screen.getByText(/Brokerages/i)).toBeInTheDocument();
    expect(screen.getByText(/Security/i)).toBeInTheDocument();
  });
});





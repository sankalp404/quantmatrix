import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { cleanup, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/render';
import Login from '../Login';

const login = vi.fn().mockResolvedValue(undefined);
const navigate = vi.fn();

// Use `var` so Vitest hoisting doesn't hit TDZ.
var locationState: any = { state: {} };

vi.mock('../../context/AuthContext', () => {
  return { useAuth: () => ({ login }) };
});

vi.mock('react-router-dom', async () => {
  const actual: any = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigate,
    useLocation: () => locationState,
  };
});

describe('Login redirect', () => {
  beforeEach(() => {
    cleanup();
    login.mockClear();
    navigate.mockClear();
    locationState = { state: {} };
    localStorage.removeItem('qm.ui.last_route');
  });

  it('redirects to saved last route after login when no state.from exists', async () => {
    const user = userEvent.setup();
    localStorage.setItem('qm.ui.last_route', '/settings/market/coverage');

    renderWithProviders(<Login />);

    await user.type(screen.getByPlaceholderText('yourname'), 'demo');
    await user.type(screen.getByPlaceholderText('••••••••'), 'pw');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => expect(login).toHaveBeenCalled());
    expect(navigate).toHaveBeenCalledWith('/settings/market/coverage', { replace: true });
  });

  it('prefers state.from over saved route', async () => {
    const user = userEvent.setup();
    localStorage.setItem('qm.ui.last_route', '/settings/profile');
    locationState = { state: { from: { pathname: '/settings/market/tracked', search: '', hash: '' } } };

    renderWithProviders(<Login />);

    await user.type(screen.getByPlaceholderText('yourname'), 'demo');
    await user.type(screen.getByPlaceholderText('••••••••'), 'pw');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => expect(login).toHaveBeenCalled());
    expect(navigate).toHaveBeenCalledWith('/settings/market/tracked', { replace: true });
  });
});



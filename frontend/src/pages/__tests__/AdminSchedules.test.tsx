import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import AdminSchedules from '../AdminSchedules';
import { renderWithProviders } from '../../test/render';

const apiGet = vi.fn();
const apiPost = vi.fn();
const apiPut = vi.fn();

vi.mock('../../services/api', () => {
  return {
    default: {
      get: (...args: any[]) => apiGet(...args),
      post: (...args: any[]) => apiPost(...args),
      put: (...args: any[]) => apiPut(...args),
      delete: vi.fn(),
    },
  };
});

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('../../hooks/useUserPreferences', () => ({
  useUserPreferences: () => ({
    currency: 'USD',
    timezone: 'America/New_York',
    tableDensity: 'comfortable',
  }),
}));

describe('AdminSchedules guided presets', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiPut.mockReset();
  });

  it('creates the hourly coverage monitor schedule using user timezone', async () => {
    apiGet.mockResolvedValueOnce({ data: { schedules: [] } }); // initial load
    apiPut.mockRejectedValueOnce({ response: { status: 404 } }); // update attempt -> not found -> create
    apiPost.mockResolvedValueOnce({ data: { status: 'ok', name: 'monitor-coverage-health-hourly' } });
    apiGet.mockResolvedValueOnce({ data: { schedules: [] } }); // reload after create

    renderWithProviders(<AdminSchedules />, { route: '/settings/admin/schedules' });

    const user = userEvent.setup();
    const btns = await screen.findAllByRole('button', { name: 'monitor-coverage-health-hourly' });
    await user.click(btns[0]);

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith('/admin/schedules', {
        name: 'monitor-coverage-health-hourly',
        task: 'backend.tasks.market_data_tasks.monitor_coverage_health',
        cron: '0 * * * *',
        timezone: 'America/New_York',
        args: [],
        kwargs: {},
        enabled: true,
      });
    });
  });

  it('updates an existing schedule via PUT when preset name already exists', async () => {
    apiGet.mockResolvedValueOnce({ data: { schedules: [{ name: 'monitor-coverage-health-hourly' }] } }); // initial load
    apiPut.mockResolvedValueOnce({ data: { status: 'ok', name: 'monitor-coverage-health-hourly' } });
    apiGet.mockResolvedValueOnce({ data: { schedules: [{ name: 'monitor-coverage-health-hourly' }] } }); // reload after update

    renderWithProviders(<AdminSchedules />, { route: '/settings/admin/schedules' });

    const user = userEvent.setup();
    // Wait for initial load to populate existing schedules so preset uses PUT (update).
    await waitFor(() => expect(apiGet).toHaveBeenCalledWith('/admin/schedules'));
    const btns = await screen.findAllByRole('button', { name: 'monitor-coverage-health-hourly' });
    await user.click(btns[0]);

    await waitFor(() => {
      expect(apiPut).toHaveBeenCalledWith('/admin/schedules/monitor-coverage-health-hourly', {
        cron: '0 * * * *',
        timezone: 'America/New_York',
        args: [],
        kwargs: {},
      });
    });
  });
});



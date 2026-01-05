import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChakraProvider } from '@chakra-ui/react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { system } from '../../theme/system';
import AdminJobs from '../AdminJobs';

const apiGet = vi.fn();

vi.mock('../../services/api', () => {
  return {
    default: {
      get: (...args: any[]) => apiGet(...args),
    },
  };
});

vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('AdminJobs', () => {
  beforeEach(() => {
    apiGet.mockReset();
  });

  it('loads first page with default paging params', async () => {
    apiGet.mockResolvedValueOnce({
      data: { jobs: [{ id: 1, task_name: 'monitor_coverage_health', status: 'ok' }], total: 200 },
    });

    render(
      <ChakraProvider value={system}>
        <AdminJobs />
      </ChakraProvider>,
    );

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith('/market-data/admin/jobs', { params: { limit: 25, offset: 0 } });
    });

    expect(await screen.findByText(/Admin Jobs/i)).toBeInTheDocument();
    expect(screen.getByText(/monitor_coverage_health/i)).toBeInTheDocument();
    expect(screen.getByText(/Showing 1 of 200 total/i)).toBeInTheDocument();
  });

  it('changes page size via pagination menu and refetches', async () => {
    apiGet
      .mockResolvedValueOnce({ data: { jobs: [], total: 4585 } }) // initial
      .mockResolvedValueOnce({ data: { jobs: [], total: 4585 } }); // after page size change

    render(
      <ChakraProvider value={system}>
        <AdminJobs />
      </ChakraProvider>,
    );

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith('/market-data/admin/jobs', { params: { limit: 25, offset: 0 } });
    });

    const user = userEvent.setup();
    await user.click(screen.getAllByRole('button', { name: /Page size/i })[0]);
    await user.click(screen.getByRole('menuitem', { name: /50 per page/i }));

    await waitFor(() => {
      expect(apiGet).toHaveBeenLastCalledWith('/market-data/admin/jobs', { params: { limit: 50, offset: 0 } });
    });
  });

  it('opens details dialog from row action', async () => {
    apiGet.mockResolvedValueOnce({
      data: {
        jobs: [
          {
            id: 1,
            task_name: 'update_tracked_symbol_cache',
            status: 'ok',
            params: { foo: 'bar' },
            counters: { symbols_processed: 12 },
            error: null,
          },
        ],
        total: 1,
      },
    });

    render(
      <ChakraProvider value={system}>
        <AdminJobs />
      </ChakraProvider>,
    );

    expect(await screen.findByText(/update_tracked_symbol_cache/i)).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /Details/i })[0]);
    expect(await screen.findByText(/Job details/i)).toBeInTheDocument();
    expect(screen.getByText(/Params/i)).toBeInTheDocument();
    expect(screen.getByText(/Counters/i)).toBeInTheDocument();
  });
});



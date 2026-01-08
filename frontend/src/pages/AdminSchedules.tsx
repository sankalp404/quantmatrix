import React from 'react';
import {
  Box,
  Button,
  Heading,
  HStack,
  Text,
  Badge,
  Input,
  IconButton,
  TooltipRoot,
  TooltipTrigger,
  TooltipPositioner,
  TooltipContent,
  DialogRoot,
  DialogBackdrop,
  DialogPositioner,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogTitle,
} from '@chakra-ui/react';
import toast from 'react-hot-toast';
import api from '../services/api';
import FormField from '../components/ui/FormField';
import { FiPlay, FiPause, FiTrash2, FiRotateCw } from 'react-icons/fi';
import SortableTable, { type Column } from '../components/SortableTable';
import { useUserPreferences } from '../hooks/useUserPreferences';

const AdminSchedules: React.FC = () => {
  const { timezone: userTimezone } = useUserPreferences();
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState<{ schedules: any[]; mode?: string } | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [form, setForm] = React.useState({ name: '', task: '', cron: '0 * * * *', timezone: userTimezone || 'UTC' });

  React.useEffect(() => {
    // Keep timezone aligned to user preference unless user already changed it in the form.
    setForm((p) => (p.timezone && p.timezone !== 'UTC' ? p : { ...p, timezone: userTimezone || 'UTC' }));
  }, [userTimezone]);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get('/admin/schedules');
      setData(r.data || null);
    } catch (err: any) {
      toast.error(err?.message || 'Failed to load schedules');
    } finally {
      setLoading(false);
    }
  };

  const create = async () => {
    if (creating) return;
    if (!form.name.trim() || !form.task.trim() || !form.cron.trim() || !form.timezone.trim()) {
      toast.error('Name, task, cron, and timezone are required');
      return;
    }
    setCreating(true);
    try {
      await api.post('/admin/schedules', {
        name: form.name.trim(),
        task: form.task.trim(),
        cron: form.cron.trim(),
        timezone: form.timezone.trim(),
        args: [],
        kwargs: {},
        enabled: true,
      });
      toast.success('Schedule created');
      setCreateOpen(false);
      setForm({ name: '', task: '', cron: '0 * * * *', timezone: userTimezone || 'UTC' });
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to create schedule');
    } finally {
      setCreating(false);
    }
  };

  type Preset = { name: string; task: string; cron: string; description: string };
  const presets: Preset[] = [
    {
      name: 'monitor-coverage-health-hourly',
      task: 'backend.tasks.market_data_tasks.monitor_coverage_health',
      cron: '0 * * * *',
      description: 'Recompute coverage snapshot hourly (keeps dashboard fresh).',
    },
    {
      name: 'restore-daily-coverage-tracked-nightly',
      task: 'backend.tasks.market_data_tasks.bootstrap_daily_coverage_tracked',
      cron: '15 2 * * *',
      description: 'Nightly: refresh tracked → daily backfill → recompute → history → coverage (no 5m).',
    },
  ];

  const upsertSchedule = async (p: Preset) => {
    const tz = (userTimezone || form.timezone || 'UTC').trim();
    try {
      // Robust upsert:
      // - Try update first (works even if the list hasn't loaded yet)
      // - If schedule doesn't exist, create it
      try {
        await api.put(`/admin/schedules/${encodeURIComponent(p.name)}`, {
          cron: p.cron,
          timezone: tz,
          args: [],
          kwargs: {},
        });
        toast.success('Schedule updated');
      } catch (err: any) {
        const status = err?.response?.status;
        if (status !== 404) throw err;
        await api.post('/admin/schedules', {
          name: p.name,
          task: p.task,
          cron: p.cron,
          timezone: tz,
          args: [],
          kwargs: {},
          enabled: true,
        });
        toast.success('Schedule created');
      }
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to apply schedule');
    }
  };

  const runNow = async (task: string) => {
    try {
      await api.post('/admin/schedules/run-now', null, { params: { task } });
      toast.success('Task enqueued');
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to enqueue task');
    }
  };

  const pause = async (name: string) => {
    try {
      await api.post('/admin/schedules/pause', null, { params: { name } });
      toast.success('Paused');
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to pause schedule');
    }
  };

  const resume = async (name: string) => {
    try {
      await api.post('/admin/schedules/resume', null, { params: { name } });
      toast.success('Resumed');
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to resume schedule');
    }
  };

  const remove = async (name: string) => {
    try {
      await api.delete(`/admin/schedules/${encodeURIComponent(name)}`);
      toast.success('Deleted');
      await load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to delete schedule');
    }
  };

  React.useEffect(() => {
    load();
  }, []);

  return (
    <Box p={0}>
      <HStack justify="space-between" mb={3}>
        <Box>
          <Heading size="md">Admin Schedules</Heading>
          <Text fontSize="sm" color="fg.muted">
            Manage Celery beat schedules (RedBeat). Create, pause/resume, run-now, and delete.
          </Text>
          <Text mt={1} fontSize="xs" color="fg.muted">
            Note: schedules run only while backend + celery beat are running (your laptop/dev stack must be up).
          </Text>
        </Box>
        <HStack gap={2}>
          <Button size="sm" variant="outline" onClick={() => setCreateOpen(true)}>
            New schedule
          </Button>
          <Button size="sm" onClick={load} loading={loading}>
            Reload
          </Button>
        </HStack>
      </HStack>

      <Box mb={3} borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card" p={3}>
        <Text fontSize="sm" fontWeight="semibold" mb={2}>
          Guided presets
        </Text>
        <Text fontSize="xs" color="fg.muted" mb={3}>
          One-click setup for the recommended market-data schedules (timezone defaults to your preference: {userTimezone || 'UTC'}).
        </Text>
        <HStack gap={2} flexWrap="wrap">
          {presets.map((p) => (
            <Button
              key={p.name}
              size="sm"
              variant="outline"
              onClick={() => void upsertSchedule(p)}
              loading={loading}
            >
              {p.name}
            </Button>
          ))}
        </HStack>
        <Box mt={2}>
          {presets.map((p) => (
            <Text key={`${p.name}-desc`} fontSize="xs" color="fg.muted">
              <Text as="span" fontFamily="mono">{p.name}</Text>: {p.description} (cron: <Text as="span" fontFamily="mono">{p.cron}</Text>)
            </Text>
          ))}
        </Box>
      </Box>

      <Box w="full" borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card">
        <SortableTable
          data={data?.schedules || []}
          columns={
            [
              {
                key: 'status',
                header: 'Status',
                accessor: (s: any) => String(s.status || (s.enabled ? 'active' : 'paused')),
                sortable: true,
                sortType: 'string',
                render: (v) => {
                  const status = String(v || '');
                  const palette = status === 'active' ? 'green' : status === 'paused' ? 'orange' : 'gray';
                  return <Badge colorPalette={palette}>{status}</Badge>;
                },
                width: '140px',
              },
              {
                key: 'name',
                header: 'Name',
                accessor: (s: any) => s.name,
                sortable: true,
                sortType: 'string',
                render: (v) => <Text fontWeight="medium">{String(v || '')}</Text>,
              },
              {
                key: 'task',
                header: 'Task',
                accessor: (s: any) => s.task,
                sortable: true,
                sortType: 'string',
                render: (v) => <Text fontFamily="mono" fontSize="12px">{String(v || '')}</Text>,
              },
              {
                key: 'cron',
                header: 'Cron',
                accessor: (s: any) => s.cron,
                sortable: true,
                sortType: 'string',
                render: (v) => <Text fontFamily="mono" fontSize="12px" color="fg.muted">{String(v || '—')}</Text>,
                width: '160px',
              },
              {
                key: 'timezone',
                header: 'Timezone',
                accessor: (s: any) => s.timezone || 'UTC',
                sortable: true,
                sortType: 'string',
                render: (v) => <Text fontSize="12px" color="fg.muted">{String(v || 'UTC')}</Text>,
                width: '120px',
              },
              {
                key: 'actions',
                header: 'Actions',
                accessor: () => null,
                sortable: false,
                isNumeric: true,
                width: '140px',
                render: (_v, s) => {
                  const status = String(s.status || (s.enabled ? 'active' : 'paused'));
                  return (
                    <HStack gap={1} justify="flex-end">
                      <TooltipRoot>
                        <TooltipTrigger asChild>
                          <IconButton
                            aria-label="Run now"
                            size="xs"
                            variant="outline"
                            onClick={() => runNow(String(s.task || ''))}
                            disabled={!s.task}
                          >
                            <FiPlay />
                          </IconButton>
                        </TooltipTrigger>
                        <TooltipPositioner>
                          <TooltipContent>Run now</TooltipContent>
                        </TooltipPositioner>
                      </TooltipRoot>
                      {status === 'paused' ? (
                        <TooltipRoot>
                          <TooltipTrigger asChild>
                            <IconButton aria-label="Resume" size="xs" variant="outline" onClick={() => resume(String(s.name))}>
                              <FiRotateCw />
                            </IconButton>
                          </TooltipTrigger>
                          <TooltipPositioner>
                            <TooltipContent>Resume</TooltipContent>
                          </TooltipPositioner>
                        </TooltipRoot>
                      ) : (
                        <TooltipRoot>
                          <TooltipTrigger asChild>
                            <IconButton aria-label="Pause" size="xs" variant="outline" onClick={() => pause(String(s.name))}>
                              <FiPause />
                            </IconButton>
                          </TooltipTrigger>
                          <TooltipPositioner>
                            <TooltipContent>Pause</TooltipContent>
                          </TooltipPositioner>
                        </TooltipRoot>
                      )}
                      <TooltipRoot>
                        <TooltipTrigger asChild>
                          <IconButton aria-label="Delete" size="xs" variant="outline" colorPalette="red" onClick={() => remove(String(s.name))}>
                            <FiTrash2 />
                          </IconButton>
                        </TooltipTrigger>
                        <TooltipPositioner>
                          <TooltipContent>Delete</TooltipContent>
                        </TooltipPositioner>
                      </TooltipRoot>
                    </HStack>
                  );
                },
              },
            ] as Column<any>[]
          }
          defaultSortBy="name"
          defaultSortOrder="asc"
          size="sm"
          maxHeight="70vh"
          emptyMessage={loading ? 'Loading…' : 'No schedules found.'}
        />
      </Box>

      <DialogRoot open={createOpen} onOpenChange={(d) => setCreateOpen(Boolean(d.open))}>
        <DialogBackdrop />
        <DialogPositioner>
          <DialogContent maxW="min(720px, calc(100vw - 32px))" w="full">
            <DialogHeader>
              <DialogTitle>New schedule</DialogTitle>
            </DialogHeader>
            <DialogBody>
              <Box display="flex" flexDirection="column" gap={4}>
                <FormField label="Name" helperText="Unique identifier for the schedule.">
                  <Input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
                </FormField>
                <FormField label="Task (dotted path)" helperText="Example: backend.tasks.market_data_tasks.monitor_coverage_health">
                  <Input value={form.task} onChange={(e) => setForm((p) => ({ ...p, task: e.target.value }))} />
                </FormField>
                <FormField label="Cron" helperText="Format: m h dom mon dow">
                  <Input value={form.cron} onChange={(e) => setForm((p) => ({ ...p, cron: e.target.value }))} />
                </FormField>
                <FormField label="Timezone">
                  <Input value={form.timezone} onChange={(e) => setForm((p) => ({ ...p, timezone: e.target.value }))} />
                </FormField>
              </Box>
            </DialogBody>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button colorScheme="brand" loading={creating} onClick={create}>
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </DialogPositioner>
      </DialogRoot>
    </Box>
  );
};

export default AdminSchedules;



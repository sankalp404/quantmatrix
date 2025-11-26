import React from 'react';
import {
  Box,
  Heading,
  Tag,
  Button,
  HStack,
  Stack,
  Text,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  FormControl,
  FormLabel,
  Input,
  Select,
  Switch,
  NumberInput,
  NumberInputField,
  useToast,
  ButtonGroup,
  Textarea,
  Flex,
  SimpleGrid,
  IconButton,
  Tooltip,
  Divider,
} from '@chakra-ui/react';
import { FiDownload, FiUpload, FiEdit3, FiPlay, FiPause, FiTrash2, FiRefreshCw } from 'react-icons/fi';
import api from '../services/api';

type CatalogEntry = {
  id: string;
  display_name: string;
  group: string;
  task: string;
  description: string;
  default_cron: string;
  default_tz: string;
  queue?: string | null;
  singleflight?: boolean;
  max_concurrency?: number;
  timeout_s?: number;
  retries?: number;
  backoff_s?: number;
};

type MetadataState = {
  queue: string;
  priority: string;
  singleflight: boolean;
  maxConcurrency: number;
  timeout: number;
  retries: number;
  backoff: number;
};

const defaultCron = '0 3 * * *';
const defaultTimezone = 'UTC';
const cronPresets = [
  { label: 'Daily 2:00 AM UTC', cron: '0 2 * * *', tz: 'UTC' },
  { label: 'Daily 2:00 AM PST', cron: '0 2 * * *', tz: 'America/Los_Angeles' },
  { label: 'Daily 6:00 AM EST', cron: '0 6 * * *', tz: 'America/New_York' },
  { label: 'Hourly', cron: '0 * * * *', tz: 'UTC' },
];

const emptyMetadata = (): MetadataState => ({
  queue: '',
  priority: '',
  singleflight: true,
  maxConcurrency: 1,
  timeout: 3600,
  retries: 0,
  backoff: 0,
});

const AdminSchedules: React.FC = () => {
  const toast = useToast();
  const [data, setData] = React.useState<any>({ schedules: [], mode: 'static' });
  const [catalog, setCatalog] = React.useState<Record<string, CatalogEntry[]>>({});
  const [form, setForm] = React.useState<{ name: string; task: string; cron: string; timezone: string }>({
    name: '',
    task: '',
    cron: defaultCron,
    timezone: defaultTimezone,
  });
  const [metadataState, setMetadataState] = React.useState<MetadataState>(emptyMetadata());
  const [preview, setPreview] = React.useState<string[]>([]);
  const modalDisclosure = useDisclosure();
  const importDisclosure = useDisclosure();
  const [importText, setImportText] = React.useState('');
  const [modalMode, setModalMode] = React.useState<'create' | 'edit'>('create');
  const [selectedSchedule, setSelectedSchedule] = React.useState<any | null>(null);
  const load = async () => {
    try {
      const r = await api.get('/admin/schedules');
      setData(r.data || { schedules: [], mode: 'static' });
    } catch { }
    try {
      const c = await api.get('/admin/tasks/catalog');
      setCatalog(c.data?.catalog || {});
    } catch { }
  };
  React.useEffect(() => { load(); }, []);

  const templateByTask = React.useMemo(() => {
    const map: Record<string, CatalogEntry> = {};
    Object.values(catalog).forEach((entries) => {
      (entries || []).forEach((entry: CatalogEntry) => {
        map[entry.task] = entry;
      });
    });
    return map;
  }, [catalog]);

  const humanizeCron = (cron?: string, tz?: string) => {
    if (!cron) return '';
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return `${cron} ${tz || ''}`;
    const [m, h, dom, mon, dow] = parts;
    const hh = Number(h);
    const mm = Number(m);
    const timeStr = (Number.isNaN(hh) || Number.isNaN(mm))
      ? `${h}:${m}${tz ? ` ${tz}` : ''}`
      : new Date(Date.UTC(2000, 0, 1, hh, mm)).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }) + (tz ? ` ${tz}` : '');
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const mapDow = (val: string) => (/^\d$/.test(val) ? dayNames[parseInt(val, 10) % 7] : val);
    if (dom === '*' && mon === '*' && dow === '*') return `Daily at ${timeStr}`;
    if (dom === '*' && mon === '*' && dow === '1-5') return `Mon–Fri at ${timeStr}`;
    if (dom === '*' && mon === '*' && /^\d(,\d)+$/.test(dow)) return `${dow.split(',').map(mapDow).join(', ')} at ${timeStr}`;
    if (dom === '*' && mon === '*' && /^\d$/.test(dow)) return `Every ${mapDow(dow)} at ${timeStr}`;
    if (h === '*' && dom === '*' && mon === '*' && dow === '*') return `Every hour at :${m.padStart(2, '0')}`;
    if (m.startsWith('*/') && h === '*' && dom === '*' && mon === '*' && dow === '*') return `Every ${m.slice(2)} minutes`;
    return `${cron}${tz ? ` (${tz})` : ''}`;
  };

  const buildMetadataPayload = (meta: MetadataState) => ({
    queue: meta.queue || undefined,
    priority: meta.priority === '' ? undefined : Number(meta.priority),
    safety: {
      singleflight: meta.singleflight,
      max_concurrency: meta.maxConcurrency,
      timeout_s: meta.timeout,
      retries: meta.retries,
      backoff_s: meta.backoff,
    },
  });

  const hydrateMetadataState = (meta: any | null | undefined): MetadataState => ({
    queue: meta?.queue ?? '',
    priority: meta?.priority?.toString?.() ?? '',
    singleflight: meta?.safety?.singleflight ?? true,
    maxConcurrency: meta?.safety?.max_concurrency ?? 1,
    timeout: meta?.safety?.timeout_s ?? 3600,
    retries: meta?.safety?.retries ?? 0,
    backoff: meta?.safety?.backoff_s ?? 0,
  });

  const updatePreview = async (cronValue: string, tzValue: string) => {
    try {
      const r = await api.get('/admin/schedules/preview', { params: { cron: cronValue, timezone: tzValue } });
      setPreview(r.data?.next_runs_utc || []);
    } catch {
      setPreview([]);
    }
  };

  const openCreateModal = (template?: CatalogEntry) => {
    const initial = {
      name: template?.id || '',
      task: template?.task || '',
      cron: template?.default_cron || defaultCron,
      timezone: template?.default_tz || defaultTimezone,
    };
    setForm(initial);
    setMetadataState(template
      ? {
        queue: template.queue || '',
        priority: '',
        singleflight: template.singleflight ?? true,
        maxConcurrency: template.max_concurrency ?? 1,
        timeout: template.timeout_s ?? 3600,
        retries: template.retries ?? 0,
        backoff: template.backoff_s ?? 0,
      }
      : emptyMetadata());
    setModalMode('create');
    setSelectedSchedule(null);
    updatePreview(initial.cron, initial.timezone);
    modalDisclosure.onOpen();
  };

  const openEditModal = (schedule: any) => {
    const cronGuess = schedule.cron || (schedule.schedule?.match(/<crontab:\s(.*?)\s\(/)?.[1]) || defaultCron;
    setForm({
      name: schedule.name,
      task: schedule.task,
      cron: cronGuess,
      timezone: schedule.timezone || defaultTimezone,
    });
    setMetadataState(hydrateMetadataState(schedule.metadata));
    setModalMode('edit');
    setSelectedSchedule(schedule);
    updatePreview(cronGuess, schedule.timezone || defaultTimezone);
    modalDisclosure.onOpen();
  };

  const handleSave = async () => {
    if (!form.name || !form.task || !form.cron) {
      toast({ title: 'Name, task, and cron are required', status: 'warning' });
      return;
    }
    const payload = {
      name: form.name.trim(),
      task: form.task,
      cron: form.cron.trim(),
      timezone: form.timezone,
      metadata: buildMetadataPayload(metadataState),
    };
    try {
      if (modalMode === 'create') {
        await api.post('/admin/schedules', payload);
        toast({ title: 'Schedule created', status: 'success' });
      } else if (selectedSchedule) {
        await api.put(`/admin/schedules/${encodeURIComponent(selectedSchedule.name)}`, {
          cron: payload.cron,
          timezone: payload.timezone,
          metadata: payload.metadata,
        });
        toast({ title: 'Schedule updated', status: 'success' });
      }
      modalDisclosure.onClose();
      load();
    } catch (err: any) {
      toast({ title: 'Failed to save schedule', description: err?.response?.data?.detail || err?.message, status: 'error' });
    }
  };

  const renderSafetySummary = (schedule: any) => {
    const safety = schedule.metadata?.safety || {};
    return (
      <Box fontSize="xs" color="gray.400">
        <Text>Single-flight: {safety.singleflight === false ? 'No' : 'Yes'}</Text>
        <Text>Max concurrency: {safety.max_concurrency ?? 1}</Text>
        <Text>Timeout: {(safety.timeout_s ?? 3600) / 60} min</Text>
      </Box>
    );
  };

  const handleExport = async () => {
    try {
      const res = await api.get('/admin/schedules/export');
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'schedules-export.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      toast({ title: 'Export failed', description: err?.message, status: 'error' });
    }
  };

  const handleImport = async () => {
    try {
      const parsed = JSON.parse(importText || '{}');
      await api.post('/admin/schedules/import', parsed);
      toast({ title: 'Schedules imported', status: 'success' });
      setImportText('');
      importDisclosure.onClose();
      load();
    } catch (err: any) {
      toast({ title: 'Import failed', description: err?.message || 'Invalid JSON', status: 'error' });
    }
  };

  const scheduleGroup = (schedule: any): string => {
    const template = templateByTask[schedule.task];
    return template?.group || 'other';
  };

  const groupedSchedules = React.useMemo(() => {
    const groups: Record<string, any[]> = {};
    (data.schedules || []).forEach((schedule: any) => {
      const group = scheduleGroup(schedule);
      groups[group] = groups[group] || [];
      groups[group].push(schedule);
    });
    return groups;
  }, [data.schedules, templateByTask]);

  const runTask = async (taskName: string) => {
    try {
      await api.post('/admin/schedules/run-now', null, { params: { task: taskName } as any });
      toast({ title: 'Task enqueued', status: 'success' });
    } catch (err: any) {
      toast({ title: 'Run-now failed', description: err?.message, status: 'error' });
    }
  };

  const pauseSchedule = async (name: string) => {
    try {
      await api.post('/admin/schedules/pause', null, { params: { name } as any });
      toast({ title: `Paused ${name}`, status: 'info' });
      load();
    } catch (err: any) {
      toast({ title: 'Pause failed', description: err?.message, status: 'error' });
    }
  };

  const resumeSchedule = async (schedule: any) => {
    const cron = window.prompt('Resume with cron (m h dom mon dow)', schedule.cron || defaultCron);
    const tz = window.prompt('Timezone', schedule.timezone || defaultTimezone);
    if (!cron) return;
    try {
      await api.post('/admin/schedules/resume', null, { params: { name: schedule.name, cron, timezone: tz || defaultTimezone } as any });
      toast({ title: `Resumed ${schedule.name}`, status: 'success' });
      load();
    } catch (err: any) {
      toast({ title: 'Resume failed', description: err?.message, status: 'error' });
    }
  };

  const deleteSchedule = async (name: string) => {
    if (!window.confirm(`Delete schedule ${name}?`)) return;
    try {
      await api.delete(`/admin/schedules/${encodeURIComponent(name)}`);
      toast({ title: `Deleted ${name}`, status: 'success' });
      load();
    } catch (err: any) {
      toast({ title: 'Delete failed', description: err?.message, status: 'error' });
    }
  };

  return (
    <Box p={4}>
      <Flex justify="space-between" align="center" mb={2}>
        <Heading size="md">Schedules <Tag ml={2}>{data.mode}</Tag></Heading>
        <HStack spacing={3}>
          <Button leftIcon={<FiDownload />} variant="outline" onClick={handleExport}>Export</Button>
          <Button leftIcon={<FiUpload />} variant="outline" onClick={importDisclosure.onOpen}>Import</Button>
          <Button colorScheme="brand" onClick={() => openCreateModal()}>Create</Button>
        </HStack>
      </Flex>
      <Text fontSize="sm" color="gray.400" mb={6}>
        Manage Celery schedules stored in RedBeat. Cron + timezone drive execution; metadata controls queue routing, concurrency, and safety limits.
      </Text>

      <Divider my={6} />
      {Object.keys(groupedSchedules).length === 0 ? (
        <Text fontSize="sm" color="gray.500">No schedules found. Use Create to add one.</Text>
      ) : (
        <Stack spacing={6}>
          {Object.entries(groupedSchedules).map(([group, schedules]) => (
            <Box key={group}>
              <Heading size="sm" mb={3}>{group.toUpperCase()}</Heading>
              <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} spacing={4}>
                {schedules.map((s: any) => {
                  const template = templateByTask[s.task];
                  const friendlyName = template?.display_name || s.name;
                  const friendlyDescription = template?.description;
                  const isPaused = s.status === 'paused';
                  return (
                    <Box key={s.name} borderWidth="1px" borderRadius="lg" p={4} bg="surface.card" borderColor="surface.border">
                      <Flex justify="space-between" align="flex-start">
                        <Box>
                          <Heading size="sm">{friendlyName}</Heading>
                          <Text fontSize="xs" color="gray.500">Schedule ID: {s.name}</Text>
                          <Text fontSize="xs" color="gray.500">Task: {s.task}</Text>
                        </Box>
                        <HStack spacing={2}>
                          {isPaused && <Tag size="sm" colorScheme="orange">Paused</Tag>}
                        </HStack>
                      </Flex>
                      {friendlyDescription && (
                        <Text fontSize="sm" color="gray.400" mt={2}>
                          {friendlyDescription}
                        </Text>
                      )}
                      <Text fontSize="sm" mt={3} fontWeight="medium">{humanizeCron(s.cron, s.timezone)}</Text>
                      <Text fontSize="xs" color="gray.500">Cron: {s.cron || s.schedule}</Text>
                      <Text fontSize="xs" color="gray.500" mt={2}>Queue: {s.metadata?.queue || 'default'}</Text>
                      <Text fontSize="xs" color="gray.500">Priority: {s.metadata?.priority ?? '—'}</Text>
                      <Box mt={3}>{renderSafetySummary(s)}</Box>
                      <Text fontSize="xs" color="gray.500" mt={3}>Last run: {s.last_run?.status || '—'} @ {s.last_run?.started_at || '—'}</Text>
                      <HStack spacing={2} mt={4} justify="flex-end">
                        <Tooltip label="Edit">
                          <IconButton aria-label="Edit schedule" icon={<FiEdit3 />} size="sm" variant="ghost" onClick={() => openEditModal(s)} />
                        </Tooltip>
                        <Tooltip label="Run now">
                          <IconButton aria-label="Run schedule" icon={<FiPlay />} size="sm" variant="ghost" onClick={() => runTask(s.task)} />
                        </Tooltip>
                        <Tooltip label="Pause">
                          <IconButton aria-label="Pause schedule" icon={<FiPause />} size="sm" variant="ghost" onClick={() => pauseSchedule(s.name)} isDisabled={isPaused} />
                        </Tooltip>
                        <Tooltip label="Resume">
                          <IconButton aria-label="Resume schedule" icon={<FiRefreshCw />} size="sm" variant="ghost" onClick={() => resumeSchedule(s)} isDisabled={!isPaused} />
                        </Tooltip>
                        <Tooltip label="Delete">
                          <IconButton aria-label="Delete schedule" icon={<FiTrash2 />} size="sm" variant="ghost" colorScheme="red" onClick={() => deleteSchedule(s.name)} />
                        </Tooltip>
                      </HStack>
                    </Box>
                  );
                })}
              </SimpleGrid>
            </Box>
          ))}
        </Stack>
      )}

      <Modal isOpen={modalDisclosure.isOpen} onClose={modalDisclosure.onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>{modalMode === 'create' ? 'Create Schedule' : `Edit ${form.name}`}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <FormControl mb={3}>
              <FormLabel>Template</FormLabel>
              <Select placeholder="Select task" value={form.task} onChange={(e) => setForm({ ...form, task: e.target.value })}>
                {Object.keys(catalog).map((group) => (
                  <optgroup key={group} label={group.toUpperCase()}>
                    {(catalog[group] || []).map((t: CatalogEntry) => (
                      <option key={t.id} value={t.task}>{t.display_name} ({t.id})</option>
                    ))}
                  </optgroup>
                ))}
              </Select>
            </FormControl>
            <FormControl mb={3}>
              <FormLabel>Name</FormLabel>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="unique-name" isDisabled={modalMode === 'edit'} />
            </FormControl>
            <FormControl mb={3}>
              <FormLabel>Cron</FormLabel>
              <Input
                value={form.cron}
                onChange={(e) => {
                  const v = e.target.value;
                  setForm({ ...form, cron: v });
                  updatePreview(v, form.timezone);
                }}
                placeholder="m h dom mon dow"
              />
              <ButtonGroup mt={2} size="xs" spacing={2}>
                {cronPresets.map((preset) => (
                  <Button
                    key={preset.label}
                    variant="outline"
                    onClick={() => {
                      setForm({ ...form, cron: preset.cron, timezone: preset.tz });
                      updatePreview(preset.cron, preset.tz);
                    }}
                  >
                    {preset.label}
                  </Button>
                ))}
              </ButtonGroup>
            </FormControl>
            <FormControl mb={3}>
              <FormLabel>Timezone</FormLabel>
              <Select value={form.timezone} onChange={(e) => {
                const tz = e.target.value;
                setForm({ ...form, timezone: tz });
                updatePreview(form.cron, tz);
              }}>
                <option value="UTC">UTC</option>
                <option value="America/Los_Angeles">America/Los_Angeles</option>
                <option value="America/New_York">America/New_York</option>
                <option value="Europe/London">Europe/London</option>
              </Select>
            </FormControl>
            {preview.length > 0 && (
              <Box fontSize="xs" color="gray.400" mb={4}>Next runs (UTC): {preview.join(', ')}</Box>
            )}
            <Heading size="sm" mb={2}>Metadata & Safety</Heading>
            <FormControl display="flex" alignItems="center" mb={3}>
              <FormLabel mb="0">Single Flight</FormLabel>
              <Switch isChecked={metadataState.singleflight} onChange={(e) => setMetadataState({ ...metadataState, singleflight: e.target.checked })} />
            </FormControl>
            <FormControl mb={3}>
              <FormLabel>Queue</FormLabel>
              <Input value={metadataState.queue} onChange={(e) => setMetadataState({ ...metadataState, queue: e.target.value })} placeholder="default" />
            </FormControl>
            <FormControl mb={3}>
              <FormLabel>Priority</FormLabel>
              <NumberInput min={0} max={9} value={metadataState.priority} onChange={(_, val) => setMetadataState({ ...metadataState, priority: Number.isNaN(val) ? '' : String(val) })}>
                <NumberInputField placeholder="optional" />
              </NumberInput>
            </FormControl>
            <HStack spacing={4} mb={3}>
              <FormControl>
                <FormLabel>Max Concurrency</FormLabel>
                <NumberInput min={1} value={metadataState.maxConcurrency} onChange={(_, val) => setMetadataState({ ...metadataState, maxConcurrency: Number.isNaN(val) ? 1 : val })}>
                  <NumberInputField />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel>Timeout (sec)</FormLabel>
                <NumberInput min={60} step={60} value={metadataState.timeout} onChange={(_, val) => setMetadataState({ ...metadataState, timeout: Number.isNaN(val) ? 3600 : val })}>
                  <NumberInputField />
                </NumberInput>
              </FormControl>
            </HStack>
            <HStack spacing={4}>
              <FormControl>
                <FormLabel>Retries</FormLabel>
                <NumberInput min={0} value={metadataState.retries} onChange={(_, val) => setMetadataState({ ...metadataState, retries: Number.isNaN(val) ? 0 : val })}>
                  <NumberInputField />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel>Backoff (sec)</FormLabel>
                <NumberInput min={0} step={5} value={metadataState.backoff} onChange={(_, val) => setMetadataState({ ...metadataState, backoff: Number.isNaN(val) ? 0 : val })}>
                  <NumberInputField />
                </NumberInput>
              </FormControl>
            </HStack>
          </ModalBody>
          <ModalFooter>
            <Button mr={3} onClick={modalDisclosure.onClose}>Cancel</Button>
            <Button colorScheme="brand" onClick={handleSave}>{modalMode === 'create' ? 'Create' : 'Update'}</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <Modal isOpen={importDisclosure.isOpen} onClose={() => { setImportText(''); importDisclosure.onClose(); }}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Import Schedules JSON</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Textarea rows={10} value={importText} onChange={(e) => setImportText(e.target.value)} placeholder='{"schedules": [...]}' />
          </ModalBody>
          <ModalFooter>
            <Button mr={3} onClick={() => { setImportText(''); importDisclosure.onClose(); }}>Cancel</Button>
            <Button colorScheme="brand" onClick={handleImport}>Import</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default AdminSchedules;

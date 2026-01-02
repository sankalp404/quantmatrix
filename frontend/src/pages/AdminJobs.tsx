import React from 'react';
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Tag,
  Text,
  Button,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
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
  Textarea,
  Input,
  Select,
  HStack,
  Stack,
  IconButton,
  SimpleGrid,
  Tooltip,
  useToast,
  RadioGroup,
  Radio,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  FiPlay,
  FiCode,
  FiCalendar,
  FiInfo,
  FiChevronLeft,
  FiChevronRight,
  FiChevronsLeft,
  FiChevronsRight,
} from 'react-icons/fi';
import api from '../services/api';
import AppDivider from '../components/ui/AppDivider';

const AdminJobs: React.FC = () => {
  const [jobs, setJobs] = React.useState<any[]>([]);
  const [catalog, setCatalog] = React.useState<any>({});
  const actionsModal = useDisclosure();
  const detailModal = useDisclosure();
  const [selectedTemplate, setSelectedTemplate] = React.useState<any>(null);
  const [actionType, setActionType] = React.useState<'run' | 'args' | 'schedule'>('run');
  const [argsText, setArgsText] = React.useState<string>('[]');
  const [kwargsText, setKwargsText] = React.useState<string>('{}');
  const [scheduleName, setScheduleName] = React.useState<string>('');
  const [scheduleCron, setScheduleCron] = React.useState<string>('0 2 * * *');
  const [scheduleTz, setScheduleTz] = React.useState<string>('UTC');
  const toast = useToast();
  const cardBg = useColorModeValue('surface.card', 'surface.base');
  const cardBorder = useColorModeValue('surface.border', 'surface.border');
  const subtleText = useColorModeValue('gray.700', 'gray.300');
  const tabListBg = useColorModeValue('surface.panel', 'surface.base');
  const tabIdleColor = useColorModeValue('gray.600', 'gray.400');
  const tabSelectedBg = useColorModeValue('white', 'brand.600');
  const tabSelectedColor = useColorModeValue('brand.600', 'white');

  const PAGE_SIZE_KEY = 'adminJobs.pageSize';
  const initialPageSize = React.useMemo(() => {
    if (typeof window === 'undefined') return '50';
    const stored = window.localStorage.getItem(PAGE_SIZE_KEY);
    if (stored === 'all') return 'all';
    if (['25', '50', '100', '200'].includes(stored || '')) return stored as string;
    return '50';
  }, []);

  const [page, setPage] = React.useState(0);
  const [pageSize, setPageSize] = React.useState<string>(initialPageSize); // '25' | '50' | '100' | '200' | 'all'
  const [total, setTotal] = React.useState<number>(0);

  const load = async (pageArg = page, pageSizeArg = pageSize) => {
    try {
      const params: any = {};
      if (pageSizeArg === 'all') {
        params.all = true;
      } else {
        const numericSize = Number(pageSizeArg) || 50;
        params.limit = numericSize;
        params.offset = pageArg * numericSize;
      }
      const r = await api.get('/market-data/admin/jobs', { params });
      setJobs(r.data?.jobs || []);
      const apiTotal = r.data?.total;
      const parsedTotal = typeof apiTotal === 'number' ? apiTotal : Number(apiTotal);
      setTotal(Number.isFinite(parsedTotal) && parsedTotal > 0 ? parsedTotal : (r.data?.jobs || []).length);
      if (pageSizeArg === 'all') {
        setPage(0);
      }
    } catch { }
    try {
      const c = await api.get('/admin/tasks/catalog');
      setCatalog(c.data?.catalog || {});
    } catch { }
  };
  React.useEffect(() => { load(); }, []);
  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(PAGE_SIZE_KEY, pageSize);
    }
  }, [pageSize]);

  const onPageChange = (nextPage: number) => {
    if (pageSize === 'all') return;
    if (nextPage < 0) return;
    const numericSize = Number(pageSize) || 50;
    const totalPages = Math.max(1, Math.ceil(total / numericSize));
    if (nextPage >= totalPages) return;
    setPage(nextPage);
    load(nextPage, pageSize);
  };

  const onPageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    const nextSize = val;
    setPageSize(nextSize);
    setPage(0);
    load(0, nextSize);
  };

  const color = (s: string) => s === 'ok' ? 'green' : (s === 'running' ? 'blue' : 'red');

  const formatTs = (value?: string | null) => (value ? new Date(value).toLocaleString() : '—');

  const summarizeCounters = (counters: any) => {
    if (!counters) return 'No counters reported';
    if (counters.summary) return counters.summary;
    const tracked = counters.tracked_total ?? counters.universe ?? counters.tracked;
    const inserted = counters.bars_inserted_total ?? counters.inserted ?? counters.updated_total;
    const uptodate = counters.up_to_date_total ?? counters.up_to_date;
    const errors = counters.errors ?? 0;
    const provider = counters.provider_usage ? Object.keys(counters.provider_usage).join(', ') : undefined;
    const parts = [];
    if (inserted !== undefined) parts.push(`Inserted ${inserted}`);
    if (uptodate !== undefined) parts.push(`${uptodate} already up-to-date`);
    if (tracked !== undefined) parts.push(`tracked ${tracked}`);
    parts.push(`${errors} errors`);
    if (provider) parts.push(`provider: ${provider.toUpperCase()}`);
    return parts.join('; ');
  };

  const jobSummary = React.useMemo(() => {
    const summary = { total: total || jobs.length, ok: 0, running: 0, error: 0 };
    jobs.forEach((job) => {
      const key = job.status as 'ok' | 'running' | 'error';
      if (summary[key] !== undefined) {
        summary[key] += 1;
      }
    });
    return summary;
  }, [jobs]);

  const formatLastRun = (lastRun?: any) => {
    if (!lastRun) return '—';
    const ts = lastRun.finished_at || lastRun.started_at;
    return `${lastRun.status}${ts ? ` @ ${formatTs(ts)}` : ''}`;
  };

  const formatTime = (hour: string, minute: string) => {
    const h = Number(hour);
    const m = Number(minute);
    if (Number.isNaN(h) || Number.isNaN(m)) return `${hour}:${minute}`;
    const meridian = h >= 12 ? 'PM' : 'AM';
    const hr12 = ((h + 11) % 12) + 1;
    return `${hr12}:${m.toString().padStart(2, '0')} ${meridian}`;
  };

  const humanizeCron = (cron: string, tz?: string) => {
    if (!cron) return '—';
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return `${cron}${tz ? ` (${tz})` : ''}`;
    const [min, hour, dom, mon, dow] = parts;
    const time = formatTime(hour, min);
    const tzLabel = tz ? ` ${tz}` : '';

    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const formatDow = (value: string) => {
      if (value === '*') return '';
      if (value === '1-5') return 'Weekdays';
      const list = value.split(',').map(v => {
        const idx = parseInt(v, 10);
        return Number.isFinite(idx) ? dayNames[(idx + 7) % 7] : v;
      });
      if (list.length === 1) return list[0];
      return list.join(', ');
    };

    if (dom === '*' && mon === '*' && dow === '*') {
      return `Daily at ${time}${tzLabel}`;
    }
    if (dom === '*' && mon === '*' && dow !== '*') {
      const dayLabel = formatDow(dow);
      return `${dayLabel || 'Specific days'} at ${time}${tzLabel}`;
    }
    if (dow === '*' && mon === '*') {
      if (dom === '1') return `Monthly on the 1st at ${time}${tzLabel}`;
      return `Monthly on day ${dom} at ${time}${tzLabel}`;
    }
    return `${cron}${tz ? ` (${tz})` : ''}`;
  };

  const runTask = async (label: string, fn: () => Promise<any>) => {
    try {
      await fn();
      toast({ title: `${label} triggered`, status: 'success', duration: 3000, isClosable: true });
      load();
    } catch (err: any) {
      toast({ title: `Failed to run ${label}`, description: err?.message || 'Unknown error', status: 'error', duration: 4000, isClosable: true });
    }
  };

  React.useEffect(() => {
    if (!actionsModal.isOpen) {
      setSelectedTemplate(null);
    }
  }, [actionsModal.isOpen]);

  const [selectedJob, setSelectedJob] = React.useState<any | null>(null);

  const openActionModal = (template: any, mode: 'run' | 'args' | 'schedule') => {
    setSelectedTemplate(template);
    setActionType(mode);
    setArgsText(JSON.stringify(template.args || [], null, 2));
    setKwargsText(JSON.stringify(template.kwargs || {}, null, 2));
    setScheduleName(template.id);
    setScheduleCron(template.default_cron || '0 2 * * *');
    setScheduleTz(template.default_tz || 'UTC');
    actionsModal.onOpen();
  };

  const handleActionSubmit = async () => {
    if (!selectedTemplate) return;
    try {
      if (actionType === 'run') {
        await runTask(selectedTemplate.display_name || selectedTemplate.id, () =>
          api.post('/admin/schedules/run-now', null, { params: { task: selectedTemplate.task } as any }),
        );
      } else if (actionType === 'args') {
        const parsedArgs = JSON.parse(argsText || '[]');
        const parsedKwargs = JSON.parse(kwargsText || '{}');
        await runTask(`${selectedTemplate.display_name || selectedTemplate.id} (args)`, () =>
          api.post('/admin/schedules/run-now', null, { params: { task: selectedTemplate.task, args: parsedArgs, kwargs: parsedKwargs } as any }),
        );
      } else if (actionType === 'schedule') {
        await runTask('Schedule created', () =>
          api.post('/admin/schedules', {
            name: scheduleName,
            task: selectedTemplate.task,
            cron: scheduleCron,
            timezone: scheduleTz,
          }),
        );
      }
      actionsModal.onClose();
    } catch (err: any) {
      toast({
        title: 'Action failed',
        description: err?.message || 'Invalid input',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    }
  };

  const formatGroupLabel = (value: string) =>
    value
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');

  const openJobDetails = (job: any) => {
    setSelectedJob(job);
    detailModal.onOpen();
  };

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Jobs</Heading>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={6}>
        <Box borderWidth="1px" borderRadius="lg" p={4} bg={cardBg} borderColor={cardBorder}>
          <Text fontSize="xs" color={subtleText}>Total Runs</Text>
          <Text fontSize="2xl" fontWeight="bold">{jobSummary.total}</Text>
        </Box>
        <Box borderWidth="1px" borderRadius="lg" p={4} bg={cardBg} borderColor={cardBorder}>
          <Text fontSize="xs" color={subtleText}>Successful</Text>
          <Text fontSize="2xl" fontWeight="bold" color="green.400">{jobSummary.ok}</Text>
        </Box>
        <Box borderWidth="1px" borderRadius="lg" p={4} bg={cardBg} borderColor={cardBorder}>
          <Text fontSize="xs" color={subtleText}>Failed</Text>
          <Text fontSize="2xl" fontWeight="bold" color="red.400">{jobSummary.error}</Text>
        </Box>
      </SimpleGrid>
      <Tabs variant="unstyled">
        <TabList
          bg={tabListBg}
          borderRadius="full"
          p={1}
          width="fit-content"
          boxShadow="inset 0 0 0 1px rgba(0,0,0,0.05)"
          mb={4}
        >
          <Tab
            borderRadius="full"
            px={4}
            py={2}
            fontWeight={600}
            color={tabIdleColor}
            _selected={{ bg: tabSelectedBg, color: tabSelectedColor, boxShadow: 'sm' }}
          >
            Catalog
          </Tab>
          <Tab
            borderRadius="full"
            px={4}
            py={2}
            fontWeight={600}
            color={tabIdleColor}
            _selected={{ bg: tabSelectedBg, color: tabSelectedColor, boxShadow: 'sm' }}
          >
            Recent Runs
          </Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            {Object.keys(catalog).map(group => (
              <Box key={group} mb={6}>
                <Heading size="sm" mb={3} color={subtleText}>{formatGroupLabel(group)}</Heading>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  {(catalog[group] || []).map((t: any) => (
                    <Box
                      key={t.id}
                      p={4}
                      borderRadius="xl"
                      border="1px solid"
                      borderColor={cardBorder}
                      bg={cardBg}
                      boxShadow="sm"
                    >
                      <Text fontWeight="semibold" fontSize="lg">{t.display_name || t.id}</Text>
                      {t.description ? (
                        <Text fontSize="sm" color={subtleText} mt={1}>{t.description}</Text>
                      ) : null}
                      <Text fontSize="sm" color={subtleText} mt={2}>
                        {humanizeCron(t.default_cron, t.default_tz || 'UTC')}
                      </Text>
                      <Text fontSize="xs" color={subtleText} mt={1}>
                        Last: {formatLastRun(t.last_run)}
                      </Text>
                      <HStack spacing={2} justify="flex-end" mt={4}>
                        <Tooltip label="Run now">
                          <IconButton
                            aria-label="Run now"
                            icon={<FiPlay />}
                            size="sm"
                            variant="ghost"
                            onClick={() => openActionModal(t, 'run')}
                          />
                        </Tooltip>
                        <Tooltip label="Run with custom args">
                          <IconButton
                            aria-label="Run with args"
                            icon={<FiCode />}
                            size="sm"
                            variant="ghost"
                            onClick={() => openActionModal(t, 'args')}
                          />
                        </Tooltip>
                        <Tooltip label="Create schedule">
                          <IconButton
                            aria-label="Schedule task"
                            icon={<FiCalendar />}
                            size="sm"
                            variant="ghost"
                            onClick={() => openActionModal(t, 'schedule')}
                          />
                        </Tooltip>
                      </HStack>
                    </Box>
                  ))}
                </SimpleGrid>
                <AppDivider mt={5} borderColor={cardBorder} opacity={0.4} />
              </Box>
            ))}
          </TabPanel>
          <TabPanel>
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>ID</Th>
                  <Th>Task</Th>
                  <Th>Status</Th>
                  <Th>Started</Th>
                  <Th>Finished</Th>
                  <Th>Summary</Th>
                  <Th></Th>
                </Tr>
              </Thead>
              <Tbody>
                {jobs.map((j) => (
                  <Tr key={j.id}>
                    <Td>{j.id}</Td>
                    <Td>{j.task_name}</Td>
                    <Td><Tag colorScheme={color(j.status)}>{j.status}</Tag></Td>
                    <Td>{formatTs(j.started_at)}</Td>
                    <Td>{formatTs(j.finished_at)}</Td>
                    <Td>
                      <Text fontSize="xs" color="gray.500">
                        {summarizeCounters(j.counters)}
                      </Text>
                    </Td>
                    <Td textAlign="right">
                      <Tooltip label="View details">
                        <IconButton
                          size="sm"
                          variant="ghost"
                          aria-label="View details"
                          icon={<FiInfo />}
                          onClick={() => openJobDetails(j)}
                        />
                      </Tooltip>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
            <HStack justify="space-between" mt={3} align="center" flexWrap="wrap" rowGap={2}>
              <Text fontSize="sm" color="gray.500">
                {(() => {
                  const numericSize = pageSize === 'all' ? total : Number(pageSize) || 50;
                  const start = pageSize === 'all' ? (total > 0 ? 1 : 0) : page * numericSize + 1;
                  const end = pageSize === 'all' ? total : Math.min(total, (page + 1) * numericSize);
                  if (!total) return `Showing ${jobs.length} of —`;
                  return `Showing ${start}–${end} of ${total} jobs${pageSize === 'all' ? ' (all)' : ''}`;
                })()}
              </Text>
              <HStack spacing={3} align="center">
                <HStack spacing={1}>
                  <Text fontSize="sm" color="gray.500">Jobs per page</Text>
                  <Select size="sm" value={pageSize} onChange={onPageSizeChange} width="110px">
                    {[25, 50, 100, 200].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                    <option value="all">All</option>
                  </Select>
                </HStack>
                {pageSize !== 'all' && (
                  <HStack spacing={2} align="center">
                    <IconButton
                      aria-label="First page"
                      icon={<FiChevronsLeft />}
                      size="sm"
                      variant="ghost"
                      onClick={() => onPageChange(0)}
                      isDisabled={page === 0}
                    />
                    <IconButton
                      aria-label="Previous page"
                      icon={<FiChevronLeft />}
                      size="sm"
                      variant="ghost"
                      onClick={() => onPageChange(page - 1)}
                      isDisabled={page === 0}
                    />
                    <Text fontSize="sm" color="gray.500">
                      Page {page + 1} of {Math.max(1, Math.ceil(total / (Number(pageSize) || 50)))}
                    </Text>
                    <IconButton
                      aria-label="Next page"
                      icon={<FiChevronRight />}
                      size="sm"
                      variant="ghost"
                      onClick={() => onPageChange(page + 1)}
                      isDisabled={(page + 1) * (Number(pageSize) || 50) >= total}
                    />
                    <IconButton
                      aria-label="Last page"
                      icon={<FiChevronsRight />}
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        const numericSize = Number(pageSize) || 50;
                        const totalPages = Math.max(1, Math.ceil(total / numericSize));
                        onPageChange(totalPages - 1);
                      }}
                      isDisabled={(page + 1) * (Number(pageSize) || 50) >= total}
                    />
                  </HStack>
                )}
              </HStack>
            </HStack>
          </TabPanel>
        </TabPanels>
      </Tabs>

      <Modal isOpen={actionsModal.isOpen} onClose={actionsModal.onClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>{selectedTemplate?.display_name || 'Run Task'}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedTemplate && (
              <>
                <Text fontSize="sm" color="gray.500" mb={3}>
                  {selectedTemplate.task}
                </Text>
                <RadioGroup value={actionType} onChange={(val) => setActionType(val as any)} mb={4}>
                  <Stack direction="row" spacing={4}>
                    <Radio value="run">Run now</Radio>
                    <Radio value="args">Run with args</Radio>
                    <Radio value="schedule">Schedule</Radio>
                  </Stack>
                </RadioGroup>
                {actionType === 'args' && (
                  <>
                    <FormControl mb={3}>
                      <FormLabel>args (JSON array)</FormLabel>
                      <Textarea value={argsText} onChange={(e) => setArgsText(e.target.value)} rows={4} />
                    </FormControl>
                    <FormControl mb={3}>
                      <FormLabel>kwargs (JSON object)</FormLabel>
                      <Textarea value={kwargsText} onChange={(e) => setKwargsText(e.target.value)} rows={4} />
                    </FormControl>
                  </>
                )}
                {actionType === 'schedule' && (
                  <>
                    <FormControl mb={3}>
                      <FormLabel>Schedule name</FormLabel>
                      <Input value={scheduleName} onChange={(e) => setScheduleName(e.target.value)} />
                    </FormControl>
                    <FormControl mb={3}>
                      <FormLabel>Cron (m h dom mon dow)</FormLabel>
                      <Input value={scheduleCron} onChange={(e) => setScheduleCron(e.target.value)} placeholder="0 2 * * *" />
                    </FormControl>
                    <FormControl mb={3}>
                      <FormLabel>Timezone</FormLabel>
                      <Input value={scheduleTz} onChange={(e) => setScheduleTz(e.target.value)} placeholder="UTC" />
                    </FormControl>
                  </>
                )}
              </>
            )}
          </ModalBody>
          <ModalFooter>
            <Button mr={3} onClick={actionsModal.onClose}>Cancel</Button>
            <Button colorScheme="brand" onClick={handleActionSubmit}>
              {actionType === 'schedule' ? 'Create schedule' : 'Run'}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
      <Modal isOpen={detailModal.isOpen} onClose={detailModal.onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Job details</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedJob && (
              <Stack spacing={4}>
                <Box>
                  <Text fontSize="xs" color="gray.500">Task</Text>
                  <Text fontWeight="semibold">{selectedJob.task_name}</Text>
                </Box>
                <HStack spacing={6}>
                  <Box>
                    <Text fontSize="xs" color="gray.500">Status</Text>
                    <Tag colorScheme={color(selectedJob.status)}>{selectedJob.status}</Tag>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="gray.500">Started</Text>
                    <Text>{formatTs(selectedJob.started_at)}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="xs" color="gray.500">Finished</Text>
                    <Text>{formatTs(selectedJob.finished_at)}</Text>
                  </Box>
                </HStack>
                <Box>
                  <Text fontSize="xs" color="gray.500">Params</Text>
                  <Box fontFamily="mono" fontSize="xs" bg="surface.panel" borderRadius="md" p={3} whiteSpace="pre-wrap">
                    {JSON.stringify(selectedJob.params || {}, null, 2)}
                  </Box>
                </Box>
                <Box>
                  <Text fontSize="xs" color="gray.500">Counters</Text>
                  <Box fontFamily="mono" fontSize="xs" bg="surface.panel" borderRadius="md" p={3} whiteSpace="pre-wrap">
                    {JSON.stringify(selectedJob.counters || {}, null, 2)}
                  </Box>
                </Box>
                {selectedJob.error ? (
                  <Box>
                    <Text fontSize="xs" color="gray.500">Error</Text>
                    <Box fontFamily="mono" fontSize="xs" bg="red.900" color="red.100" borderRadius="md" p={3} whiteSpace="pre-wrap">
                      {selectedJob.error}
                    </Box>
                  </Box>
                ) : null}
              </Stack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button onClick={detailModal.onClose}>Close</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default AdminJobs;



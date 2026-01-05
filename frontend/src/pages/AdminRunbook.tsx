import React from 'react';
import {
  Box,
  Heading,
  SimpleGrid,
  Text,
  Button,
  VStack,
  HStack,
  Badge,
  Icon,
  useDisclosure,
  DialogRoot,
  DialogBackdrop,
  DialogPositioner,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from '@chakra-ui/react';
import hotToast from 'react-hot-toast';
import { FiZap, FiRefreshCw, FiShield, FiLayers } from 'react-icons/fi';
import { triggerTaskByName } from '../utils/taskActions';
import AppDivider from '../components/ui/AppDivider';

const runbooks = [
  {
    title: 'Bootstrap Universe',
    description: 'Runs the full refresh → tracked → backfills → indicators chain.',
    icon: FiZap,
    accent: 'purple.300',
    steps: [
      { label: 'Bootstrap Universe', task: 'bootstrap_universe' },
    ],
  },
  {
    title: 'Coverage Reset Chain',
    description: 'Runs the full refresh → tracked → daily + 5m backfills → recompute → history → monitor.',
    icon: FiLayers,
    accent: 'teal.300',
    steps: [
      { label: 'Refresh Constituents', task: 'refresh_index_constituents' },
      { label: 'Update Tracked Symbols', task: 'update_tracked_symbol_cache' },
      { label: 'Backfill Daily Bars', task: 'backfill_last_200_bars' },
      { label: 'Backfill 5m Bars', task: 'backfill_5m_last_n_days' },
      { label: 'Recompute Indicators', task: 'recompute_indicators_universe' },
      { label: 'Record History', task: 'record_daily_history' },
      { label: 'Monitor Coverage Health', task: 'monitor_coverage_health' },
    ],
  },
  {
    title: 'Refresh + Update Tracked',
    description: 'Use after editing watchlists or when indexes rebalance.',
    icon: FiRefreshCw,
    accent: 'cyan.300',
    steps: [
      { label: 'Refresh Constituents', task: 'refresh_index_constituents' },
      { label: 'Update Tracked Symbols', task: 'update_tracked_symbol_cache' },
      { label: 'Backfill New Tracked', task: 'backfill_new_tracked' },
    ],
  },
  {
    title: 'Fix Coverage / Freshness',
    description: 'Brings coverage back within SLA when the dashboard shows alerts.',
    icon: FiShield,
    accent: 'orange.300',
    steps: [
      { label: 'Backfill Daily', task: 'backfill_last_200_bars' },
      { label: 'Backfill 5m', task: 'backfill_5m_last_n_days' },
      { label: 'Recompute Indicators', task: 'recompute_indicators_universe' },
      { label: 'Record History', task: 'record_daily_history' },
    ],
  },
];

const AdminRunbook: React.FC = () => {
  const [running, setRunning] = React.useState<string | null>(null);
  const [selectedRunbook, setSelectedRunbook] = React.useState<any>(null);
  const confirmModal = useDisclosure();
  const toast = (args: { title: string; description?: string; status?: 'success' | 'error' | 'info' | 'warning'; duration?: number; isClosable?: boolean }) => {
    const msg = args.description ? `${args.title}: ${args.description}` : args.title;
    if (args.status === 'success') return hotToast.success(args.title);
    if (args.status === 'error') return hotToast.error(msg);
    return hotToast(msg);
  };
  const cardBg = 'bg.card';
  const cardBorder = 'border.subtle';
  const chipBg = 'bg.muted';
  const chipColor = 'fg.muted';
  const metaText = 'fg.muted';
  const headingColor = 'fg.default';
  const stepLabelColor = 'fg.default';
  const taskIdColor = 'fg.muted';

  const runSequence = async (title: string, steps: { label: string; task: string }[]) => {
    setRunning(title);
    try {
      for (const step of steps) {
        await triggerTaskByName(step.task);
      }
      toast({ title: `${title} triggered`, status: 'success', duration: 4000, isClosable: true });
    } catch (err: any) {
      toast({
        title: `Failed to run ${title}`,
        description: err?.message || 'Unknown error',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setRunning(null);
    }
  };

  const handleRunbookClick = (book: any) => {
    setSelectedRunbook(book);
    confirmModal.onOpen();
  };

  const executeRunbook = async () => {
    if (!selectedRunbook) return;
    await runSequence(selectedRunbook.title, selectedRunbook.steps);
    confirmModal.onClose();
  };

  return (
    <Box p={4}>
      <Heading size="md" mb={4} color={headingColor}>Admin Runbook</Heading>
      <Text color={metaText} mb={6}>
        Guided flows for the most common operational tasks. Review the steps, then trigger the full sequence from a single modal.
      </Text>
      <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4}>
        {runbooks.map((book) => (
          <Box
            key={book.title}
            border="1px solid"
            borderColor={cardBorder}
            bg={cardBg}
            borderRadius="xl"
            p={4}
            display="flex"
            flexDirection="column"
            gap={3}
          >
            <HStack gap={3}>
              <Box
                borderRadius="full"
                bg={chipBg}
                w="40px"
                h="40px"
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <Icon as={book.icon} color={book.accent} boxSize={5} />
              </Box>
              <Box>
                <Heading size="sm" color={headingColor}>{book.title}</Heading>
                <Text fontSize="sm" color={metaText}>{book.description}</Text>
              </Box>
            </HStack>
            <VStack align="stretch" gap={2}>
              {book.steps.map((step, idx) => (
                <HStack key={step.task} gap={3}>
                  <Badge borderRadius="full" bg={chipBg} color={chipColor} px={2} py={1} fontSize="xs">
                    {idx + 1}
                  </Badge>
                  <Box flex="1">
                    <Text fontWeight="medium" color={stepLabelColor}>{step.label}</Text>
                    <Text fontSize="xs" color={taskIdColor}>{step.task}</Text>
                  </Box>
                </HStack>
              ))}
            </VStack>
            <AppDivider borderColor={cardBorder} opacity={0.5} />
            <Button
              colorScheme="brand"
              variant="solid"
              onClick={() => handleRunbookClick(book)}
            >
              Review & Run
            </Button>
          </Box>
        ))}
      </SimpleGrid>

      <DialogRoot open={confirmModal.open} onOpenChange={(d) => { if (!d.open) confirmModal.onClose(); }}>
        <DialogBackdrop />
        <DialogPositioner>
          <DialogContent maxW="min(760px, calc(100vw - 32px))" w="full">
            <DialogHeader>
              <DialogTitle>{selectedRunbook?.title}</DialogTitle>
            </DialogHeader>
            <DialogBody>
              <DialogDescription>
                {selectedRunbook?.description}
              </DialogDescription>
              <VStack align="stretch" gap={3} mt={4}>
                {selectedRunbook?.steps?.map((step: any, idx: number) => (
                  <HStack key={step.task} gap={3}>
                    <Badge borderRadius="full" px={2} py={1} fontSize="xs" bg={chipBg} color={chipColor}>
                      {idx + 1}
                    </Badge>
                    <Box>
                      <Text fontWeight="medium">{step.label}</Text>
                      <Text fontSize="xs" color="fg.muted">{step.task}</Text>
                    </Box>
                  </HStack>
                ))}
              </VStack>
            </DialogBody>
            <DialogFooter>
              <Button mr={3} onClick={confirmModal.onClose}>Cancel</Button>
              <Button
                colorScheme="brand"
                loading={running === selectedRunbook?.title}
                onClick={executeRunbook}
              >
                Run sequence
              </Button>
            </DialogFooter>
          </DialogContent>
        </DialogPositioner>
      </DialogRoot>
    </Box>
  );
};

export default AdminRunbook;


import React from 'react';
import {
  Box,
  Heading,
  SimpleGrid,
  Text,
  Button,
  Stack,
  useToast,
  HStack,
  Tag,
  Icon,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Divider,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiZap, FiRefreshCw, FiShield, FiLayers } from 'react-icons/fi';
import { triggerTaskByName } from '../utils/taskActions';

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
  const toast = useToast();
  const cardBg = useColorModeValue('surface.card', 'surface.base');
  const cardBorder = useColorModeValue('surface.border', 'surface.border');
  const chipBg = useColorModeValue('gray.200', 'rgba(255,255,255,0.08)');
  const chipColor = useColorModeValue('gray.700', 'gray.200');
  const metaText = useColorModeValue('gray.700', 'gray.300');
  const headingColor = useColorModeValue('gray.900', 'gray.100');
  const stepLabelColor = useColorModeValue('gray.800', 'gray.100');
  const taskIdColor = useColorModeValue('gray.600', 'gray.400');

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
      <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} spacing={4}>
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
            <HStack spacing={3}>
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
            <Stack spacing={2}>
              {book.steps.map((step, idx) => (
                <HStack key={step.task} spacing={3}>
                  <Tag size="sm" borderRadius="full" bg={chipBg} color={chipColor}>
                    {idx + 1}
                  </Tag>
                  <Box flex="1">
                    <Text fontWeight="medium" color={stepLabelColor}>{step.label}</Text>
                    <Text fontSize="xs" color={taskIdColor}>{step.task}</Text>
                  </Box>
                </HStack>
              ))}
            </Stack>
            <Divider borderColor={cardBorder} opacity={0.5} />
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

      <Modal isOpen={confirmModal.isOpen} onClose={confirmModal.onClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>{selectedRunbook?.title}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text fontSize="sm" color="gray.500" mb={4}>
              {selectedRunbook?.description}
            </Text>
            <Stack spacing={3}>
              {selectedRunbook?.steps.map((step: any, idx: number) => (
                <HStack key={step.task} spacing={3}>
                  <Tag size="sm" variant="subtle" colorScheme="purple">
                    {idx + 1}
                  </Tag>
                  <Box>
                    <Text fontWeight="medium">{step.label}</Text>
                    <Text fontSize="xs" color="gray.500">{step.task}</Text>
                  </Box>
                </HStack>
              ))}
            </Stack>
          </ModalBody>
          <ModalFooter>
            <Button mr={3} onClick={confirmModal.onClose}>Cancel</Button>
            <Button
              colorScheme="brand"
              isLoading={running === selectedRunbook?.title}
              onClick={executeRunbook}
            >
              Run sequence
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default AdminRunbook;


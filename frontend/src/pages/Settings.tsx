import React, { useEffect, useMemo, useState } from 'react';
import { Box, Text, Card, CardBody, useColorModeValue, VStack, HStack, Input, Select, Button, Table, Thead, Tr, Th, Tbody, Td, Badge, useToast, Link as CLink, Tooltip, SimpleGrid, Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, useDisclosure, InputGroup, InputRightElement, IconButton, Image, useColorMode, AlertDialog, AlertDialogOverlay, AlertDialogContent, AlertDialogHeader, AlertDialogBody, AlertDialogFooter } from '@chakra-ui/react';
import { accountsApi, aggregatorApi, handleApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { FiExternalLink, FiEye, FiEyeOff, FiTrash2 } from 'react-icons/fi';
import SchwabLogo from '../assets/logos/schwab.svg';
import TastytradeLogo from '../assets/logos/tastytrade.svg';
import IbkrLogo from '../assets/logos/interactive-brokers.svg';

const Settings: React.FC = () => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const toast = useToast();
  const { user } = useAuth();
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ broker: 'SCHWAB', account_number: '', account_name: '', account_type: 'TAXABLE' });
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [cfg, setCfg] = useState<{ schwabConfigured: boolean; redirect?: string; schwabProbe?: any } | null>(null);
  const [tt, setTt] = useState<{ connected: boolean; available: boolean; last_error?: string } | null>(null);
  const [ttForm, setTtForm] = useState({ username: '', password: '', mfa_code: '' });
  // Wizard
  const wizard = useDisclosure();
  const [step, setStep] = useState<number>(1);
  const [broker, setBroker] = useState<'SCHWAB' | 'TASTYTRADE' | 'IBKR' | ''>('');
  const [schwabForm, setSchwabForm] = useState({ account_number: '', account_name: '' });
  const [ibkrForm, setIbkrForm] = useState({ flex_token: '', query_id: '' });
  const [busy, setBusy] = useState(false);
  const [showTtPw, setShowTtPw] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const {
    isOpen: isDeleteOpen,
    onOpen: onDeleteOpen,
    onClose: onDeleteClose,
  } = useDisclosure();
  const cancelRef = React.useRef<HTMLButtonElement>(null);

  const brokerDisplayName = (b: string) => {
    const key = (b || '').toUpperCase();
    if (key === 'IBKR') return 'Interactive Brokers';
    if (key === 'SCHWAB') return 'Charles Schwab';
    if (key === 'TASTYTRADE') return 'Tastytrade';
    return b;
  };

  const LogoTile: React.FC<{ label: string; srcs: string[]; selected: boolean; onClick: () => void; wide?: boolean }> =
    ({ label, srcs, selected, onClick, wide }) => {
      const [idx, setIdx] = React.useState(0);
      const { colorMode } = useColorMode();
      const src = srcs[Math.min(idx, srcs.length - 1)];
      return (
        <Box
          as="div"
          aria-label={label}
          onClick={onClick}
          cursor="pointer"
          bg="transparent"
          border="0"
          rounded="md"
          p={1}
          _hover={{ transform: 'scale(1.03)' }}
          _active={{ transform: 'scale(0.98)' }}
          display="flex"
          alignItems="center"
          justifyContent="center"
          minH={wide ? "44px" : "60px"}
          minW={wide ? "150px" : "60px"}
        >
          <Image
            src={src}
            alt={label}
            height={wide ? "40px" : "56px"}
            width={wide ? "150px" : "56px"}
            objectFit="contain"
            filter={colorMode === 'dark' ? undefined : undefined}
            onError={() => {
              if (idx < srcs.length - 1) setIdx(idx + 1);
            }}
          />
        </Box>
      );
    };

  const loadAccounts = async () => {
    try {
      const res: any = await accountsApi.list();
      setAccounts(res || []);
    } catch (e) {
      toast({ title: 'Load accounts failed', description: handleApiError(e), status: 'error' });
    }
  };

  useEffect(() => {
    const init = async () => {
      loadAccounts();
      try {
        const conf: any = await aggregatorApi.config();
        setCfg({ schwabConfigured: !!conf?.schwab?.configured, redirect: conf?.schwab?.redirect_uri, schwabProbe: conf?.schwab?.probe });
        try {
          const s: any = await aggregatorApi.tastytradeStatus();
          setTt({ connected: !!s?.connected, available: !!s?.available, last_error: s?.last_error });
        } catch { /* ignore */ }
      } catch {
        setCfg({ schwabConfigured: false });
      }
    };
    init();
  }, []);

  const handleAdd = async () => {
    setAdding(true);
    try {
      await accountsApi.add({
        broker: form.broker,
        account_number: form.account_number.trim(),
        account_name: form.account_name.trim() || undefined,
        account_type: form.account_type,
      });
      await loadAccounts();
      setForm({ broker: 'SCHWAB', account_number: '', account_name: '', account_type: 'TAXABLE' });
      toast({ title: 'Account added', status: 'success' });
    } catch (e) {
      toast({ title: 'Add account failed', description: handleApiError(e), status: 'error' });
    } finally {
      setAdding(false);
    }
  };

  const handleConnectSchwab = async (id: number) => {
    try {
      if (cfg && !cfg.schwabConfigured) {
        toast({ title: 'Schwab OAuth not configured', description: 'Ask admin to set client_id, secret, and redirect URI on the server.', status: 'warning' });
        return;
      }
      const res: any = await aggregatorApi.schwabLink(id, false);
      const url = res?.url;
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
        toast({ title: 'Complete Schwab connect in the new tab', status: 'info' });
      }
    } catch (e) {
      toast({ title: 'Link failed', description: handleApiError(e), status: 'error' });
    }
  };

  const pollSyncStatus = async (id: number) => {
    setSyncingId(id);
    try {
      for (let i = 0; i < 20; i++) {
        const s: any = await accountsApi.syncStatus(id);
        if (s?.sync_status && !['queued', 'running'].includes(String(s.sync_status).toLowerCase())) {
          break;
        }
        await new Promise(r => setTimeout(r, 1000));
      }
    } finally {
      setSyncingId(null);
      await loadAccounts();
    }
  };

  const handleSync = async (id: number) => {
    try {
      const res: any = await accountsApi.sync(id, 'comprehensive');
      if (res?.task_id || res?.status) {
        pollSyncStatus(id);
        toast({ title: 'Sync started', status: 'success' });
      }
    } catch (e) {
      toast({ title: 'Sync failed', description: handleApiError(e), status: 'error' });
    }
  };

  const handleTTConnect = async () => {
    try {
      setBusy(true);
      const res: any = await aggregatorApi.tastytradeConnect({ username: ttForm.username.trim(), password: ttForm.password, mfa_code: ttForm.mfa_code?.trim() || undefined });
      const jobId = res?.job_id;
      if (!jobId) throw new Error('Connect job not started');
      // Fast path: if already connected, short-circuit
      try {
        const s0: any = await aggregatorApi.tastytradeStatus();
        if (s0?.connected) {
          setTt({ connected: true, available: true });
          toast({ title: 'Tastytrade connected', status: 'success' });
          await loadAccounts();
          return;
        }
      } catch { /* ignore */ }
      // Poll status
      for (let i = 0; i < 30; i++) {
        const st: any = await aggregatorApi.tastytradeStatus(jobId);
        if (st?.job_state === 'success' || st?.connected) {
          setTt({ connected: true, available: true });
          toast({ title: 'Tastytrade connected', status: 'success' });
          await loadAccounts();
          break;
        }
        if (st?.job_state === 'error') {
          throw new Error(st?.job_error || st?.last_error || 'Login failed');
        }
        await new Promise(r => setTimeout(r, 1000));
      }
    } catch (e) {
      toast({ title: 'Connect failed', description: handleApiError(e), status: 'error' });
    } finally {
      setBusy(false);
    }
  };

  const handleTTDisconnect = async () => {
    try {
      await aggregatorApi.tastytradeDisconnect();
      setTt({ connected: false, available: true });
      toast({ title: 'Tastytrade disconnected', status: 'success' });
      await loadAccounts();
    } catch (e) {
      toast({ title: 'Disconnect failed', description: handleApiError(e), status: 'error' });
    }
  };

  // Wizard helpers
  const startWizard = () => {
    setStep(1);
    setBroker('');
    setSchwabForm({ account_number: '', account_name: '' });
    setIbkrForm({ flex_token: '', query_id: '' });
    wizard.onOpen();
  };

  const submitWizard = async () => {
    try {
      setBusy(true);
      if (broker === 'SCHWAB') {
        // Create placeholder Schwab account then open OAuth link
        const added: any = await accountsApi.add({
          broker: 'SCHWAB',
          account_number: (schwabForm.account_number || 'SCHWAB_OAUTH').trim(),
          account_name: schwabForm.account_name.trim() || undefined,
          account_type: 'TAXABLE'
        });
        const newId = added?.id || (await (async () => { await loadAccounts(); const a = accounts.find(x => String(x.account_number).includes(schwabForm.account_number || 'SCHWAB_OAUTH') && String(x.broker).toLowerCase() === 'schwab'); return a?.id; })());
        if (!newId) throw new Error('Failed to create Schwab account');
        const res: any = await aggregatorApi.schwabLink(newId, false);
        const url = res?.url;
        if (!url) throw new Error('Authorization URL not returned');
        window.open(url, '_blank', 'noopener,noreferrer');
        toast({ title: 'Complete Schwab connect in the new tab', status: 'info' });
      } else if (broker === 'TASTYTRADE') {
        // Use form already shown on page? Keep wizard support as well
        if (!ttForm.username || !ttForm.password) throw new Error('Enter Tastytrade username and password');
        const res: any = await aggregatorApi.tastytradeConnect({ username: ttForm.username.trim(), password: ttForm.password, mfa_code: ttForm.mfa_code?.trim() || undefined });
        const jobId = res?.job_id;
        if (!jobId) throw new Error('Connect job not started');
        // Fast path: if already connected, short-circuit
        try {
          const s0: any = await aggregatorApi.tastytradeStatus();
          if (s0?.connected) {
            toast({ title: 'Tastytrade connected', status: 'success' });
            await loadAccounts();
            wizard.onClose();
            return;
          }
        } catch { /* ignore */ }
        for (let i = 0; i < 30; i++) {
          const st: any = await aggregatorApi.tastytradeStatus(jobId);
          if (st?.job_state === 'success' || st?.connected) {
            toast({ title: 'Tastytrade connected', status: 'success' });
            await loadAccounts();
            wizard.onClose();
            break;
          }
          if (st?.job_state === 'error') {
            throw new Error(st?.job_error || st?.last_error || 'Login failed');
          }
          await new Promise(r => setTimeout(r, 1000));
        }
      } else if (broker === 'IBKR') {
        if (!ibkrForm.flex_token || !ibkrForm.query_id) throw new Error('Enter Flex Token and Query ID');
        const res: any = await aggregatorApi.ibkrFlexConnect({ flex_token: ibkrForm.flex_token.trim(), query_id: ibkrForm.query_id.trim() });
        const jobId = res?.job_id;
        if (!jobId) throw new Error('Connect job not started');
        // Fast path check
        try {
          const s0: any = await aggregatorApi.ibkrFlexStatus();
          if (s0?.connected || (Array.isArray(s0?.accounts) && s0.accounts.length > 0)) {
            toast({ title: 'Interactive Brokers connected', status: 'success' });
            await loadAccounts();
            wizard.onClose();
            return;
          }
        } catch { /* ignore */ }
        for (let i = 0; i < 30; i++) {
          const st: any = await aggregatorApi.ibkrFlexStatus();
          if (st?.connected || (Array.isArray(st?.accounts) && st.accounts.length > 0)) {
            toast({ title: 'Interactive Brokers connected', status: 'success' });
            await loadAccounts();
            wizard.onClose();
            break;
          }
          await new Promise(r => setTimeout(r, 1000));
        }
      }
      wizard.onClose();
    } catch (e) {
      toast({ title: 'Connection failed', description: handleApiError(e), status: 'error' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box p={2}>
      <Card bg={cardBg} border="1px" borderColor={borderColor} mb={6}>
        <CardBody>
          <VStack align="stretch" spacing={4}>
            <HStack justify="space-between">
              <Text fontWeight="bold">Brokerages</Text>
              <Button onClick={startWizard}>+ New connection</Button>
            </HStack>
            <Text color="gray.500" fontSize="sm">Use the wizard to add new connections. Connected portfolios appear below.</Text>
          </VStack>
        </CardBody>
      </Card>
      <Card bg={cardBg} border="1px" borderColor={borderColor}>
        <CardBody>
          <VStack align="stretch" spacing={4}>
            <HStack justify="space-between">
              <Text fontWeight="bold">Linked Accounts</Text>
              <Button size="sm" onClick={loadAccounts}>Refresh</Button>
            </HStack>
            {accounts.length === 0 && (
              <Box border="1px dashed" borderColor={borderColor} p={6} borderRadius="md" textAlign="center">
                <Text fontSize="sm" color="gray.500">No accounts yet. Add a brokerage account to get started.</Text>
              </Box>
            )}
            <Table size="sm">
              <Thead>
                <Tr>
                  <Th>Broker</Th>
                  <Th>Account</Th>
                  <Th>Type</Th>
                  <Th>Status</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {accounts.map((a) => {
                  return (
                    <Tr key={a.id}>
                      <Td>{brokerDisplayName(String(a.broker))}</Td>
                      <Td>{a.account_name || a.account_number}</Td>
                      <Td>{a.account_type}</Td>
                      <Td>
                        <Badge colorScheme={a.is_enabled ? 'green' : 'gray'}>{a.status}</Badge>
                        {' '}
                        {a.sync_status && <Badge variant="outline">{a.sync_status}</Badge>}
                      </Td>
                      <Td>
                        <HStack>
                          {String(a.broker || '').toLowerCase() === 'schwab' && (
                            <Tooltip label={cfg && !cfg.schwabConfigured ? 'Schwab OAuth not configured on server' : ''} isDisabled={!(cfg && !cfg.schwabConfigured)}>
                              <Button size="xs" variant="outline" onClick={() => handleConnectSchwab(a.id)} isDisabled={!!(cfg && !cfg.schwabConfigured)}>
                                Connect Charles Schwab <FiExternalLink style={{ marginLeft: 8 }} />
                              </Button>
                            </Tooltip>
                          )}
                          <Button size="xs" isLoading={syncingId === a.id} onClick={() => handleSync(a.id)}>Sync</Button>
                          <Button size="xs" variant="outline" onClick={async () => {
                            try {
                              await accountsApi.remove?.(a.id);
                              toast({ title: 'Account disabled', status: 'success' });
                              loadAccounts();
                            } catch (e) {
                              toast({ title: 'Disable failed', description: handleApiError(e), status: 'error' });
                            }
                          }}>
                            Disable
                          </Button>
                          <IconButton
                            aria-label="Delete account"
                            size="xs"
                            variant="ghost"
                            colorScheme="red"
                            icon={<FiTrash2 />}
                            onClick={() => { setDeleteId(a.id); onDeleteOpen(); }}
                          />
                        </HStack>
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </VStack>
        </CardBody>
      </Card>
      <AlertDialog
        isOpen={isDeleteOpen}
        leastDestructiveRef={cancelRef}
        onClose={() => { if (!deleteLoading) { onDeleteClose(); setDeleteId(null); } }}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Broker Account
            </AlertDialogHeader>
            <AlertDialogBody>
              This will permanently remove the broker account connection and stored credentials for this user. You can re-connect later. Continue?
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={() => { if (!deleteLoading) { onDeleteClose(); setDeleteId(null); } }}>
                Cancel
              </Button>
              <Button colorScheme="red" ml={3} isLoading={deleteLoading} onClick={async () => {
                if (!deleteId) return;
                setDeleteLoading(true);
                try {
                  await accountsApi.remove?.(deleteId);
                  toast({ title: 'Account deleted', status: 'success' });
                  await loadAccounts();
                } catch (e) {
                  toast({ title: 'Delete failed', description: handleApiError(e), status: 'error' });
                } finally {
                  setDeleteLoading(false);
                  setDeleteId(null);
                  onDeleteClose();
                }
              }}>
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
      <Modal isOpen={wizard.isOpen} onClose={wizard.onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>New Brokerage Connection</ModalHeader>
          <ModalBody>
            {step === 1 && (
              <VStack align="stretch" spacing={4}>
                <Text color="gray.500">Choose a broker to connect</Text>
                <SimpleGrid columns={{ base: 3, md: 3 }} spacing={6}>
                  <LogoTile label="Charles Schwab" srcs={[SchwabLogo]} selected={broker === 'SCHWAB'} onClick={() => setBroker('SCHWAB')} wide />
                  <LogoTile label="Tastytrade" srcs={[TastytradeLogo]} selected={broker === 'TASTYTRADE'} onClick={() => setBroker('TASTYTRADE')} wide />
                  <LogoTile label="Interactive Brokers" srcs={[IbkrLogo]} selected={broker === 'IBKR'} onClick={() => setBroker('IBKR')} wide />
                </SimpleGrid>
                <Text fontSize="sm" color="gray.500">More brokers coming soon (Fidelity, Robinhood, Public)</Text>
              </VStack>
            )}
            {step === 2 && broker === 'SCHWAB' && (
              <VStack align="stretch" spacing={3}>
                <Text fontWeight="semibold">Schwab OAuth</Text>
                <Text fontSize="sm" color="gray.500">We’ll create a placeholder account and send you to Schwab to authorize. Ensure your redirect URI matches the portal exactly.</Text>
                <HStack>
                  <Input placeholder="Account Number (optional)" value={schwabForm.account_number} onChange={(e) => setSchwabForm({ ...schwabForm, account_number: e.target.value })} />
                  <Input placeholder="Account Name (optional)" value={schwabForm.account_name} onChange={(e) => setSchwabForm({ ...schwabForm, account_name: e.target.value })} />
                </HStack>
                {cfg?.redirect && <Text fontSize="xs" color="gray.500">Redirect: {cfg.redirect}</Text>}
              </VStack>
            )}
            {step === 2 && broker === 'TASTYTRADE' && (
              <VStack align="stretch" spacing={3}>
                <Text fontWeight="semibold">Tastytrade Credentials</Text>
                <HStack>
                  <Input placeholder="Username" value={ttForm.username} onChange={(e) => setTtForm({ ...ttForm, username: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') submitWizard(); }} />
                  <InputGroup>
                    <Input placeholder="Password" type={showTtPw ? 'text' : 'password'} value={ttForm.password} onChange={(e) => setTtForm({ ...ttForm, password: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') submitWizard(); }} />
                    <InputRightElement>
                      <IconButton aria-label={showTtPw ? 'Hide password' : 'Show password'} icon={showTtPw ? <FiEyeOff /> : <FiEye />} size="sm" variant="ghost" onClick={() => setShowTtPw(!showTtPw)} />
                    </InputRightElement>
                  </InputGroup>
                </HStack>
                <Input placeholder="MFA Code (if prompted)" value={ttForm.mfa_code} onChange={(e) => setTtForm({ ...ttForm, mfa_code: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') submitWizard(); }} />
                <Text fontSize="xs" color="gray.500">We never store plain credentials; secrets are encrypted.</Text>
              </VStack>
            )}
            {step === 2 && broker === 'IBKR' && (
              <VStack align="stretch" spacing={3}>
                <Text fontWeight="semibold">IBKR Flex Query</Text>
                <Input placeholder="Flex Token" value={ibkrForm.flex_token} onChange={(e) => setIbkrForm({ ...ibkrForm, flex_token: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') submitWizard(); }} />
                <Input placeholder="Query ID" value={ibkrForm.query_id} onChange={(e) => setIbkrForm({ ...ibkrForm, query_id: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') submitWizard(); }} />
                <Text fontSize="xs" color="gray.500">Use FlexQuery token and query ID for read-only import.</Text>
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <HStack>
              {step > 1 && <Button variant="ghost" onClick={() => setStep(step - 1)}>Back</Button>}
              {step < 2 && <Button onClick={() => broker ? setStep(2) : null} isDisabled={!broker}>Next</Button>}
              {step === 2 && <Button isLoading={busy} onClick={submitWizard}>Connect</Button>}
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default Settings; 
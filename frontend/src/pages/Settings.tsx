import React, { useEffect, useMemo, useState } from 'react';
import { Box, Text, Card, CardBody, useColorModeValue, VStack, HStack, Input, Select, Button, Table, Thead, Tr, Th, Tbody, Td, Badge, useToast, Link as CLink, Tooltip } from '@chakra-ui/react';
import { accountsApi, aggregatorApi, handleApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { ExternalLinkIcon } from '@chakra-ui/icons';

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
  const [cfg, setCfg] = useState<{ schwabConfigured: boolean; redirect?: string } | null>(null);

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
        setCfg({ schwabConfigured: !!conf?.schwab?.configured, redirect: conf?.schwab?.redirect_uri });
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

  return (
    <Box p={2}>
      <Text fontSize="2xl" fontWeight="bold" mb={6}>Settings</Text>
      <Card bg={cardBg} border="1px" borderColor={borderColor} mb={6}>
        <CardBody>
          <VStack align="stretch" spacing={4}>
            <Text fontWeight="bold">Add Broker Account</Text>
            <HStack>
              <Select value={form.broker} onChange={(e) => setForm({ ...form, broker: e.target.value })} maxW="200px">
                <option value="SCHWAB">Schwab</option>
                <option value="IBKR" disabled>IBKR (coming soon)</option>
                <option value="TASTYTRADE" disabled>TastyTrade (coming soon)</option>
              </Select>
              <Input placeholder="Account Number" value={form.account_number} onChange={(e) => setForm({ ...form, account_number: e.target.value })} />
              <Input placeholder="Account Name (optional)" value={form.account_name} onChange={(e) => setForm({ ...form, account_name: e.target.value })} />
              <Select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })} maxW="200px">
                <option value="TAXABLE">Taxable</option>
                <option value="IRA">IRA</option>
                <option value="ROTH_IRA">Roth IRA</option>
                <option value="HSA">HSA</option>
                <option value="TRUST">Trust</option>
                <option value="BUSINESS">Business</option>
              </Select>
              <Button onClick={handleAdd} isLoading={adding}>Add</Button>
            </HStack>
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
                      <Td textTransform="capitalize">{a.broker}</Td>
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
                                Connect Schwab <ExternalLinkIcon ml={2} />
                              </Button>
                            </Tooltip>
                          )}
                          <Button size="xs" isLoading={syncingId === a.id} onClick={() => handleSync(a.id)}>Sync</Button>
                          <Button size="xs" variant="ghost" colorScheme="red" onClick={async () => {
                            try {
                              await accountsApi.remove?.(a.id);
                              toast({ title: 'Account disabled', status: 'success' });
                              loadAccounts();
                            } catch (e) {
                              toast({ title: 'Disable failed', description: handleApiError(e), status: 'error' });
                            }
                          }}>Disable</Button>
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
    </Box>
  );
};

export default Settings; 
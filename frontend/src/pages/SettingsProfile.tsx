import React from 'react';
import { Box, HStack, VStack, Text, Input, Button, InputGroup, IconButton } from '@chakra-ui/react';
import { PageHeader } from '../components/ui/Page';
import AppCard from '../components/ui/AppCard';
import AppDivider from '../components/ui/AppDivider';
import hotToast from 'react-hot-toast';
import { authApi, handleApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { FiEye, FiEyeOff } from 'react-icons/fi';

const SettingsProfile: React.FC = () => {
  const { user, refreshMe } = useAuth();
  const [fullName, setFullName] = React.useState(user?.full_name || '');
  const [email, setEmail] = React.useState(user?.email || '');
  const [currentPasswordForEmail, setCurrentPasswordForEmail] = React.useState('');
  const [savingProfile, setSavingProfile] = React.useState(false);

  const [currentPassword, setCurrentPassword] = React.useState('');
  const [newPassword, setNewPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [savingPassword, setSavingPassword] = React.useState(false);
  const [showPw, setShowPw] = React.useState(false);
  const [showNewPw, setShowNewPw] = React.useState(false);

  React.useEffect(() => {
    setFullName(user?.full_name || '');
    setEmail(user?.email || '');
  }, [user?.full_name, user?.email]);

  const saveProfile = async () => {
    try {
      setSavingProfile(true);
      const payload: any = {};
      if (fullName !== (user?.full_name || '')) payload.full_name = fullName;
      if (email !== (user?.email || '')) payload.email = email;
      if (payload.email && currentPasswordForEmail) payload.current_password = currentPasswordForEmail;
      if (Object.keys(payload).length === 0) {
        hotToast('No changes to save');
        return;
      }
      await authApi.updateMe(payload);
      await refreshMe();
      setCurrentPasswordForEmail('');
      hotToast.success('Profile updated');
    } catch (e) {
      hotToast.error(handleApiError(e));
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async () => {
    try {
      if (!newPassword || newPassword.length < 8) {
        hotToast.error('New password must be at least 8 characters');
        return;
      }
      if (newPassword !== confirmPassword) {
        hotToast.error('New passwords do not match');
        return;
      }
      setSavingPassword(true);
      await authApi.changePassword({
        current_password: (user?.has_password ? currentPassword : undefined),
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      hotToast.success(user?.has_password ? 'Password updated' : 'Password set');
    } catch (e) {
      hotToast.error(handleApiError(e));
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <Box w="full">
      <Box w="full" maxW="960px" mx="auto">
        <PageHeader title="Profile" subtitle="Update your personal info and security settings." />
        <VStack align="stretch" gap={4}>
          <AppCard>
            <VStack align="stretch" gap={4}>
              <Text fontWeight="semibold">Account</Text>
              <HStack gap={4} align="start" flexWrap="wrap">
                <Box minW={{ base: "100%", md: "280px" }}>
                  <Text fontSize="sm" color="fg.muted" mb={1}>Username</Text>
                  <Input value={user?.username || ''} disabled />
                </Box>
                <Box flex="1" minW={{ base: "100%", md: "320px" }}>
                  <Text fontSize="sm" color="fg.muted" mb={1}>Full name</Text>
                  <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your name" />
                </Box>
              </HStack>

              <HStack gap={4} align="start" flexWrap="wrap">
                <Box flex="1" minW={{ base: "100%", md: "320px" }}>
                  <Text fontSize="sm" color="fg.muted" mb={1}>Email</Text>
                  <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@domain.com" />
                </Box>
                {user?.has_password ? (
                  <Box minW={{ base: "100%", md: "320px" }}>
                    <Text fontSize="sm" color="fg.muted" mb={1}>Current password (required to change email)</Text>
                    <InputGroup
                      endElement={
                        <IconButton
                          aria-label={showPw ? 'Hide password' : 'Show password'}
                          size="sm"
                          variant="ghost"
                          onClick={() => setShowPw(!showPw)}
                        >
                          {showPw ? <FiEyeOff /> : <FiEye />}
                        </IconButton>
                      }
                    >
                      <Input
                        aria-label="Current password for email change"
                        type={showPw ? 'text' : 'password'}
                        value={currentPasswordForEmail}
                        onChange={(e) => setCurrentPasswordForEmail(e.target.value)}
                        placeholder="Email change password"
                      />
                    </InputGroup>
                  </Box>
                ) : null}
              </HStack>

              <HStack justify="flex-end">
                <Button loading={savingProfile} onClick={saveProfile}>
                  Save changes
                </Button>
              </HStack>
            </VStack>
          </AppCard>

          <AppCard>
            <VStack align="stretch" gap={4}>
              <Text fontWeight="semibold">Password</Text>
              <Text fontSize="sm" color="fg.muted">
                {user?.has_password
                  ? 'Change your password.'
                  : 'No password is set for this account yet. Set one to enable password-based login.'}
              </Text>
              <HStack gap={4} align="start" flexWrap="wrap">
                {user?.has_password ? (
                  <Box minW={{ base: "100%", md: "320px" }}>
                    <Text fontSize="sm" color="fg.muted" mb={1}>Current password</Text>
                    <Input
                      aria-label="Current password for password change"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="Current password"
                    />
                  </Box>
                ) : null}
                <Box minW={{ base: "100%", md: "320px" }}>
                  <Text fontSize="sm" color="fg.muted" mb={1}>New password</Text>
                  <InputGroup
                    endElement={
                      <IconButton
                        aria-label={showNewPw ? 'Hide password' : 'Show password'}
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowNewPw(!showNewPw)}
                      >
                        {showNewPw ? <FiEyeOff /> : <FiEye />}
                      </IconButton>
                    }
                  >
                    <Input
                      type={showNewPw ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 8 characters"
                    />
                  </InputGroup>
                </Box>
                <Box minW={{ base: "100%", md: "320px" }}>
                  <Text fontSize="sm" color="fg.muted" mb={1}>Confirm new password</Text>
                  <Input
                    type={showNewPw ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                  />
                </Box>
              </HStack>

              <AppDivider />
              <HStack justify="flex-end">
                <Button loading={savingPassword} onClick={savePassword}>
                  {user?.has_password ? 'Change password' : 'Set password'}
                </Button>
              </HStack>
            </VStack>
          </AppCard>
        </VStack>
      </Box>
    </Box>
  );
};

export default SettingsProfile;



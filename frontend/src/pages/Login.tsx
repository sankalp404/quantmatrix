import React, { useState } from 'react';
import { Button, Input, VStack, Text, InputGroup, IconButton, Box } from '@chakra-ui/react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FiEye, FiEyeOff } from 'react-icons/fi';
import toast from 'react-hot-toast';
import AuthLayout from '../components/layout/AuthLayout';
import AppCard from '../components/ui/AppCard';
import FormField from '../components/ui/FormField';

const Login: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <AppCard>
        <VStack as="form" gap={4} align="stretch" onSubmit={handleSubmit}>
          <Box>
            <Text fontSize="xl" fontWeight="semibold" letterSpacing="-0.02em" color="fg.default">
              Log in
            </Text>
            <Text mt={1} fontSize="sm" color="fg.muted">
              Welcome back. Enter your credentials to continue.
            </Text>
          </Box>
          <FormField label="Username" required>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="yourname" />
          </FormField>
          <FormField label="Password" required>
            <InputGroup
              endElement={
                <IconButton
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowPw(!showPw)}
                  color="fg.muted"
                >
                  {showPw ? <FiEyeOff /> : <FiEye />}
                </IconButton>
              }
            >
              <Input type={showPw ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </InputGroup>
          </FormField>
          <Button
            type="submit"
            loading={loading}
            bg="brand.500"
            _hover={{ bg: 'brand.400' }}
            _active={{ bg: 'brand.600' }}
            borderRadius="lg"
            h={11}
          >
            Login
          </Button>
          <Text fontSize="sm" color="fg.muted">
            No account? <Link to="/register" style={{ color: '#2A79F0' }}>Register</Link>
          </Text>
        </VStack>
      </AppCard>
    </AuthLayout>
  );
};

export default Login;



import React, { useState } from 'react';
import { Box, Button, Card, CardBody, FormControl, FormLabel, Input, VStack, Heading, Text, useToast } from '@chakra-ui/react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Login: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      toast({ title: 'Login failed', description: err?.response?.data?.detail || err?.message, status: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={8} maxW="420px" mx="auto">
      <Card>
        <CardBody>
          <VStack as="form" spacing={4} align="stretch" onSubmit={handleSubmit}>
            <Heading size="md">Log in</Heading>
            <FormControl isRequired>
              <FormLabel>Username</FormLabel>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="yourname" />
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Password</FormLabel>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </FormControl>
            <Button type="submit" isLoading={loading}>Login</Button>
            <Text fontSize="sm" color="gray.400">No account? <Link to="/register">Register</Link></Text>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default Login;



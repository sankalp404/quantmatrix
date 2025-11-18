import React, { useState } from 'react';
import { Box, Button, Card, CardBody, FormControl, FormLabel, Input, VStack, Heading, Text, useToast } from '@chakra-ui/react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Register: React.FC = () => {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(username, email, password, fullName);
      navigate('/');
    } catch (err: any) {
      toast({ title: 'Registration failed', description: err?.response?.data?.detail || err?.message, status: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box p={8} maxW="520px" mx="auto">
      <Card>
        <CardBody>
          <VStack as="form" spacing={4} align="stretch" onSubmit={handleSubmit}>
            <Heading size="md">Create account</Heading>
            <FormControl isRequired>
              <FormLabel>Username</FormLabel>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="yourname" />
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Email</FormLabel>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </FormControl>
            <FormControl>
              <FormLabel>Full name</FormLabel>
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Optional" />
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Password</FormLabel>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </FormControl>
            <Button type="submit" isLoading={loading}>Register</Button>
            <Text fontSize="sm" color="gray.400">Already have an account? <Link to="/login">Log in</Link></Text>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default Register;



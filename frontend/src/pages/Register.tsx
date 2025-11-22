import React, { useState } from 'react';
import { Box, Button, Card, CardBody, FormControl, FormLabel, Input, VStack, Heading, Text, useToast, InputGroup, InputRightElement, IconButton } from '@chakra-ui/react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ViewIcon, ViewOffIcon } from '@chakra-ui/icons';

const Register: React.FC = () => {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
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
              <InputGroup>
                <Input type={showPw ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
                <InputRightElement>
                  <IconButton aria-label={showPw ? 'Hide password' : 'Show password'} icon={showPw ? <ViewOffIcon /> : <ViewIcon />} size="sm" variant="ghost" onClick={() => setShowPw(!showPw)} />
                </InputRightElement>
              </InputGroup>
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



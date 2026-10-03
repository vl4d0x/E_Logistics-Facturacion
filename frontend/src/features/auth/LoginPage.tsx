import {
  Alert,
  Box,
  Button,
  Center,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/useAuth";

interface LoginFormValues {
  email: string;
  password: string;
}

export function LoginPage() {
  const { user, login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm<LoginFormValues>({
    initialValues: { email: "", password: "" },
    validate: {
      // No exige formato de correo: un operador puede entrar con un identificador sin
      // "@" (`01-architecture §5`, `fase-1-catalogos` H1.2).
      email: (value) => (value.trim().length > 0 ? null : "Requerido"),
      password: (value) => (value.length > 0 ? null : "Requerido"),
    },
  });

  if (user) {
    return <Navigate to={user.rol === "admin" ? "/admin" : "/operador"} replace />;
  }

  async function handleSubmit(values: LoginFormValues) {
    setError(null);
    setLoading(true);
    try {
      await login(values.email, values.password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Center mih="100vh" style={{ background: "var(--el-bg)" }}>
      <Paper withBorder p="xl" radius={14} w={360} style={{ borderColor: "var(--el-line)" }}>
        <Stack gap="lg">
          <Box>
            <Title order={2}>Elogistics</Title>
            <Text c="dimmed" size="sm">
              Facturación · inicia sesión
            </Text>
          </Box>

          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack gap="md">
              {error && (
                <Alert color="red" variant="light">
                  {error}
                </Alert>
              )}
              <TextInput
                label="Usuario o correo"
                placeholder="tu@correo.mx"
                required
                {...form.getInputProps("email")}
              />
              <PasswordInput
                label="Contraseña"
                placeholder="••••••••"
                required
                {...form.getInputProps("password")}
              />
              <Button type="submit" fullWidth loading={loading}>
                Entrar
              </Button>
            </Stack>
          </form>
        </Stack>
      </Paper>
    </Center>
  );
}

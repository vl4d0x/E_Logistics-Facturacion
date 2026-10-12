import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";

import { MantineProvider } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { theme } from "./theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

// Avisos: abajo a la derecha en escritorio (arriba están los botones de cada pantalla); en
// el teléfono, arriba al centro, para no tapar los botones del pie ("Viaje terminado", subir acuse).
function Avisos() {
  const telefono = useMediaQuery("(max-width: 767px)");
  return <Notifications position={telefono ? "top-center" : "bottom-right"} />;
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <MantineProvider theme={theme}>
      <Avisos />
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MantineProvider>
  );
}

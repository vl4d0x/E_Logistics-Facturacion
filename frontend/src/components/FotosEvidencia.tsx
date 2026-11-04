// Fotos de evidencia opcionales del servicio (cualquier cliente). Se adjuntan al correo de la
// factura. Antes de subirlas se reducen a ~1600 px en JPEG para que el correo no pese de más.
import { ActionIcon, FileButton, Group, Image, Loader, SimpleGrid, Stack, Text, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPhotoPlus, IconTrash } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { Card } from "./Card";

export interface FotoEvidencia {
  id: string;
  url: string | null;
  mime: string;
  nombre: string | null;
}

const LADO_MAX = 1600;

/** Reduce la foto (JPEG, lado mayor ≤ 1600 px). Si el navegador no la puede leer (p. ej. HEIC), va tal cual. */
export async function reducirFoto(file: File): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file);
    const escala = Math.min(1, LADO_MAX / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * escala);
    canvas.height = Math.round(bitmap.height * escala);
    canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/jpeg", 0.82));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch {
    return file;
  }
}

export async function subirFotoEvidencia(servicioId: string, file: File) {
  const form = new FormData();
  form.append("file", await reducirFoto(file));
  return api.post<FotoEvidencia>(`/api/v1/servicios/${servicioId}/fotos-evidencia`, form);
}

const clave = (servicioId: string) => ["servicios", servicioId, "fotos-evidencia"];

/** Tarjeta para ver, agregar y quitar las fotos de un servicio ya creado. */
export function FotosEvidenciaCard({ servicioId }: { servicioId: string }) {
  const client = useQueryClient();
  const { data: fotos, isLoading } = useQuery({
    queryKey: clave(servicioId),
    queryFn: () => api.get<FotoEvidencia[]>(`/api/v1/servicios/${servicioId}/fotos-evidencia`),
  });
  const refrescar = () => client.invalidateQueries({ queryKey: clave(servicioId) });
  const error = (title: string) => (err: unknown) =>
    notifications.show({ color: "red", title, message: err instanceof ApiError ? err.message : "Error inesperado" });
  const subir = useMutation({
    mutationFn: async (files: File[]) => {
      for (const f of files) await subirFotoEvidencia(servicioId, f);
    },
    onSettled: refrescar,
    onError: error("No se subió la foto"),
  });
  const borrar = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/fotos-evidencia/${id}`),
    onSettled: refrescar,
    onError: error("No se quitó la foto"),
  });

  return (
    <Card>
      <Group justify="space-between" mb="xs">
        <div>
          <Text fw={600}>Fotos de evidencia</Text>
          <Text size="xs" c="dimmed">
            Opcional. Se adjuntan al correo de la factura.
          </Text>
        </div>
        <FileButton accept="image/*" multiple onChange={(fs) => fs.length && subir.mutate(fs)}>
          {(props) => (
            <Tooltip label="Agregar fotos">
              <ActionIcon {...props} variant="light" size="lg" aria-label="Agregar fotos" loading={subir.isPending}>
                <IconPhotoPlus size={18} />
              </ActionIcon>
            </Tooltip>
          )}
        </FileButton>
      </Group>
      {isLoading ? (
        <Loader size="sm" />
      ) : !fotos?.length ? (
        <Text size="sm" c="dimmed">
          Sin fotos.
        </Text>
      ) : (
        <SimpleGrid cols={3} spacing="xs">
          {fotos.map((f) => (
            <Stack key={f.id} gap={2} pos="relative">
              <a href={f.url ?? undefined} target="_blank" rel="noreferrer">
                <Image src={f.url} h={90} radius="sm" fit="cover" alt={f.nombre ?? "Foto de evidencia"} />
              </a>
              <ActionIcon
                pos="absolute"
                top={4}
                right={4}
                size="sm"
                color="red"
                variant="filled"
                aria-label="Quitar foto"
                loading={borrar.isPending && borrar.variables === f.id}
                onClick={() => borrar.mutate(f.id)}
              >
                <IconTrash size={12} />
              </ActionIcon>
            </Stack>
          ))}
        </SimpleGrid>
      )}
    </Card>
  );
}

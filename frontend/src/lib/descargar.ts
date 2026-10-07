// Descarga un archivo de la API con el token (los endpoints exigen Bearer, no sirve un `<a href>`).
import { notifications } from "@mantine/notifications";
import { getAccessToken } from "./auth";

export async function descargarArchivo(path: string, nombreSugerido: string): Promise<void> {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const res = await fetch(`${base}${path}`, { headers: { Authorization: `Bearer ${getAccessToken()}` } });
  if (!res.ok) {
    notifications.show({ color: "red", title: "No se pudo descargar", message: "El servidor rechazó la descarga." });
    return;
  }
  const nombre = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? nombreSugerido;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}

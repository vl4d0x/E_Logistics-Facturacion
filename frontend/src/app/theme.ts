// Tema de Mantine — copiado tal cual de `specs/05-ui-spec.md §4`. No editar a mano;
// si cambia la marca, se actualiza ahí primero.
import { createTheme, type MantineColorsTuple } from "@mantine/core";

const red: MantineColorsTuple = [
  "#FDECEC",
  "#FAD4D5",
  "#F3A9AB",
  "#EC7E81",
  "#E75A5E",
  "#E44145",
  "#E0353B",
  "#B4272C",
  "#8E1E22",
  "#6B1518",
]; // primaryShade 6 = #E0353B

export const theme = createTheme({
  primaryColor: "brandRed",
  primaryShade: 6,
  colors: { brandRed: red },
  fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
  headings: { fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", fontWeight: "600" },
  defaultRadius: 10,
  // superficies/neutros van como CSS vars (`theme.css`, ver §2 del spec), porque los
  // grises de Mantine no matchean los tonos cálidos de la marca.
});

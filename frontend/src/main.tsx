import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppProviders } from "./app/providers";
import { AppRouter } from "./app/router";
import { UpdatePrompt } from "./app/UpdatePrompt";
import "./app/theme.css";
import "./app/responsive.css";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders>
      <AppRouter />
      <UpdatePrompt />
    </AppProviders>
  </StrictMode>,
);

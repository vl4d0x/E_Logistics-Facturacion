import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppProviders } from "../../app/providers";
import { clearSession } from "../../lib/auth";
import { LoginPage } from "./LoginPage";

function renderLoginPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </AppProviders>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    clearSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearSession();
  });

  it("renders the login form", () => {
    renderLoginPage();
    expect(screen.getByText("Elogistics")).toBeInTheDocument();
    expect(screen.getByLabelText(/correo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
  });

  it("requires the login identifier", async () => {
    const user = userEvent.setup();
    renderLoginPage();

    // Un espacio satisface el `required` nativo del input pero no el validador de
    // mantine (`value.trim()`), que es lo que de verdad queremos probar aquí.
    await user.type(screen.getByLabelText(/correo/i), " ");
    await user.type(screen.getByLabelText(/contraseña/i), "secret123");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText("Requerido")).toBeInTheDocument();
  });

  it("accepts a login identifier without email format (operador sin correo, 01-architecture §5)", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ error: { message: "x" } }), { status: 401 }));

    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText(/correo/i), "enrique");
    await user.type(screen.getByLabelText(/contraseña/i), "secret123");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init?.body as string)).toMatchObject({ email: "enrique" });
  });

  it("shows the API error message on failed login", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: "unauthorized", message: "Credenciales inválidas" } }),
        { status: 401 },
      ),
    );

    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText(/correo/i), "admin@test.mx");
    await user.type(screen.getByLabelText(/contraseña/i), "wrong");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText("Credenciales inválidas")).toBeInTheDocument();
  });
});

import { test, expect } from "@playwright/test";

test("profile load/save recovery preserves edits and clears optional fields", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("/register");
  await page.getByPlaceholder("Nume complet").fill("Profil Fictiv");
  await page.getByPlaceholder("Email", { exact: true }).fill(`profile-${Date.now()}-${info.project.name}@example.com`);
  await page.getByPlaceholder("Parolă (min. 8 caractere)").fill("Testing-pass-123!");
  await page.getByRole("button", { name: "Creează cont", exact: true }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.route("**/patients/me", route => route.fulfill({ status: 503,
    contentType: "application/json", body: JSON.stringify({ detail: "Profil temporar indisponibil" }) }));
  await page.goto("/profile");
  await expect(page.getByRole("alert").filter({ hasText: "Profil temporar indisponibil" })).toBeVisible();
  await page.unroute("**/patients/me");
  await page.getByRole("button", { name: "Reîncearcă încărcarea profilului" }).click();
  await page.getByLabel("Prenume", { exact: true }).fill("Ana Fictivă");
  await page.getByLabel("Data nașterii").fill("1990-01-02");
  await page.getByRole("combobox", { name: /^Sex/ }).selectOption("female");
  await page.route("**/patients/me", route => route.fulfill({ status: 503,
    contentType: "application/json", body: JSON.stringify({ detail: "Salvare temporar indisponibilă" }) }));
  await page.getByRole("button", { name: "Salvează", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Salvare temporar indisponibilă" })).toBeVisible();
  await expect(page.getByLabel("Prenume", { exact: true })).toHaveValue("Ana Fictivă");
  await page.unroute("**/patients/me");
  await page.getByRole("button", { name: "Salvează", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Profil salvat." })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Prenume", { exact: true })).toHaveValue("Ana Fictivă");
  await expect(page.getByLabel("Data nașterii")).toHaveValue("1990-01-02");
  await page.getByLabel("Data nașterii").fill("");
  await page.getByRole("combobox", { name: /^Sex/ }).selectOption("");
  await page.getByRole("button", { name: "Salvează", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Profil salvat." })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Data nașterii")).toHaveValue("");
  await expect(page.getByRole("combobox", { name: /^Sex/ })).toHaveValue("");
  expect(errors).toEqual([]);
  await page.goto("/settings");
  await page.getByRole("button", { name: "Șterge contul", exact: true }).click();
  await page.getByPlaceholder("Parola", { exact: true }).fill("Testing-pass-123!");
  await page.getByRole("button", { name: "Confirmă ștergerea" }).click();
  await expect(page).toHaveURL(/login/);
});

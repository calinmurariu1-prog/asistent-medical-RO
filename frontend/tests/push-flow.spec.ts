import {test, expect} from "@playwright/test";

test("settings distinguishes simulated and failed push delivery", async ({page}, info) => {
  await page.goto("/register");
  await page.getByPlaceholder("Nume complet").fill("Notificări Fictive");
  await page.getByPlaceholder("Email", {exact:true}).fill(`push-${Date.now()}-${info.project.name}@example.com`);
  await page.getByPlaceholder("Parolă (min. 8 caractere)").fill("Testing-pass-123!");
  await page.getByRole("button", {name:"Creează cont", exact:true}).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto("/settings");
  let response = {delivered:0, simulated:1, failed:0, devices:1};
  await page.route("**/api/v1/notifications/test-push", route => route.fulfill({json:response}));
  await page.getByRole("button", {name:"Trimite o notificare de test"}).click();
  await expect(page.getByText(/Nu s-a trimis nicio notificare reală/)).toBeVisible();
  response = {delivered:0, simulated:0, failed:1, devices:1};
  await page.getByRole("button", {name:"Trimite o notificare de test"}).click();
  await expect(page.getByText(/Dispozitivele au fost păstrate pentru reîncercare/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole("button", {name:"Șterge contul",exact:true}).click();
  await page.getByPlaceholder("Parola", {exact:true}).fill("Testing-pass-123!");
  await page.getByRole("button", {name:"Confirmă ștergerea",exact:true}).click();
  await expect(page).toHaveURL(/login\?deleted=complete/);
});

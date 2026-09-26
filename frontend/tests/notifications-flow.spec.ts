import {test, expect} from "@playwright/test";

test("notification inbox preserves future reminders and opens appointment", async ({page}, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await page.goto("/register");
  await page.getByPlaceholder("Nume complet").fill("Mesaje Fictive");
  await page.getByPlaceholder("Email", {exact:true}).fill(`inbox-${Date.now()}-${info.project.name}@example.com`);
  await page.getByPlaceholder("Parolă (min. 8 caractere)").fill("Testing-pass-123!");
  await page.getByRole("button", {name:"Creează cont", exact:true}).click();
  await expect(page).toHaveURL(/dashboard/);
  const appointmentId = await page.evaluate(async () => {
    const headers = {"Content-Type":"application/json"};
    const message = await fetch("/api/v1/notifications", {method:"POST", headers,
      body:JSON.stringify({title:"Mesaj fictiv curent", body:"Conținut fictiv pentru verificare."})});
    if (!message.ok) throw new Error("Cannot create test notification");
    const appointment = await fetch("/api/v1/appointments", {method:"POST", headers,
      body:JSON.stringify({title:"Consultație fictivă viitoare", starts_at:"2030-05-01T10:00:00Z"})});
    if (!appointment.ok) throw new Error("Cannot create test appointment");
    return (await appointment.json()).id;
  });
  await page.getByRole("link", {name:"Deschide notificările",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Notificări",exact:true})).toBeVisible();
  await expect(page.getByRole("heading", {name:"Mesaj fictiv curent",exact:true})).toBeVisible();
  await expect(page.getByRole("button", {name:"Viitoare (1)",exact:true})).toBeVisible();
  await page.getByRole("button", {name:"Marchează toate notificările curente citite"}).click();
  await expect(page.getByRole("button", {name:"Necitite (0)",exact:true})).toBeVisible();
  await page.getByRole("button", {name:"Viitoare (1)",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Programare: Consultație fictivă viitoare",exact:true})).toBeVisible();
  await expect(page.getByRole("button", {name:"Marchează citită",exact:true})).toHaveCount(0);
  await page.getByRole("link", {name:"Deschide programarea",exact:true}).click();
  await expect(page).toHaveURL(new RegExp(`/appointments#appointment-${appointmentId}$`));
  await expect(page.locator(`#appointment-${appointmentId}`)).toBeInViewport();
  await page.goto("/notifications");
  await page.getByRole("button", {name:"Toate (2)",exact:true}).click();
  await expect(page.getByText("Citită", {exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({path:`../docs/screenshots/notifications-${info.project.name}.png`,fullPage:true,animations:"disabled"});
  await page.getByRole("button", {name:"Comută tema"}).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.screenshot({path:`../docs/screenshots/notifications-dark-${info.project.name}.png`,fullPage:true,animations:"disabled"});
  await page.getByRole("button", {name:"Viitoare (1)",exact:true}).click();
  await page.getByRole("button", {name:"Șterge notificarea",exact:true}).click();
  await page.getByRole("button", {name:"Păstrează notificarea"}).click();
  await expect(page.getByRole("heading", {name:"Programare: Consultație fictivă viitoare",exact:true})).toBeVisible();
  await page.getByRole("button", {name:"Șterge notificarea",exact:true}).click();
  await page.getByRole("button", {name:"Confirmă ștergerea",exact:true}).click();
  await expect(page.getByRole("button", {name:"Viitoare (0)",exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", {name:"Toate (1)",exact:true})).toBeVisible();
  await page.goto("/settings");
  await page.getByRole("button", {name:"Șterge contul",exact:true}).click();
  await page.getByPlaceholder("Parola", {exact:true}).fill("Testing-pass-123!");
  await page.getByRole("button", {name:"Confirmă ștergerea",exact:true}).click();
  await expect(page).toHaveURL(/login\?deleted=complete/);
  expect(errors).toEqual([]);
});

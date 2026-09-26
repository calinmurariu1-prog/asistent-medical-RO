import {test, expect} from "@playwright/test";

test("chat shows sources, abstains and preserves a failed question", async ({page}, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/register");
  await page.getByPlaceholder("Nume complet").fill("Chat Fictiv");
  await page.getByPlaceholder("Email", {exact:true}).fill(`chat-${Date.now()}-${info.project.name}@example.com`);
  await page.getByPlaceholder("Parolă (min. 8 caractere)").fill("Testing-pass-123!");
  await page.getByRole("button", {name:"Creează cont", exact:true}).click();
  await expect(page).toHaveURL(/dashboard/);
  const lab = await page.request.post("/api/v1/labs", {
    headers: {Origin: "http://localhost:3012"},
    data: {analyte:"Glicemie", value:90, unit:"mg/dL", ref_low:70, ref_high:99},
  });
  expect(lab.ok()).toBeTruthy();
  await page.goto("/chat");
  const question = page.getByLabel("Întrebarea ta", {exact:true});
  await expect(question).toBeEnabled();
  await question.fill("Ce arată Glicemie?");
  await page.getByRole("button", {name:"Trimite întrebarea"}).click();
  await expect(page.getByRole("link", {name:"[S1] Glicemie", exact:true})).toBeVisible();
  await question.fill("Explică fractura claviculei");
  await page.getByRole("button", {name:"Trimite întrebarea"}).click();
  await expect(page.getByText(/Nu am suficiente informații și surse relevante/)).toBeVisible();
  await question.fill("Nu pot respira");
  await page.getByRole("button", {name:"Trimite întrebarea"}).click();
  await expect(page.getByText(/Acest mesaj de siguranță este generat local/)).toBeVisible();
  await expect(page.getByRole("link", {name:"[E1] Serviciul de urgență 112"})).toHaveAttribute(
    "href", "https://serviciipublice.gov.ro/serviciu/serviciul-de-urgenta-112-asigurat-cetatenilor",
  );
  await page.route("**/chats/*/messages", route => route.fulfill({
    status:403, contentType:"application/json", body:JSON.stringify({detail:"Acordul AI este necesar în Setări."}),
  }));
  await question.fill("Întrebare păstrată");
  await page.getByRole("button", {name:"Trimite întrebarea"}).click();
  await expect(page.getByRole("alert").filter({hasText:"Acordul AI"})).toContainText("Acordul AI");
  await expect(question).toHaveValue("Întrebare păstrată");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  expect(errors).toEqual([]);
});

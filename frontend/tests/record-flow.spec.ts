import {test,expect} from "@playwright/test";

test("medical record create, edit, cancel deletion and delete",async({page},info)=>{
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  await page.goto("/register");
  await page.getByPlaceholder("Nume complet").fill("Dosar Fictiv");
  await page.getByPlaceholder("Email",{exact:true}).fill(`record-${Date.now()}-${info.project.name}@example.com`);
  await page.getByPlaceholder("Parolă (min. 8 caractere)").fill("Testing-pass-123!");
  await page.getByRole("button",{name:"Creează cont",exact:true}).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto("/record");
  await expect(page.getByRole("heading",{name:"Dosar medical",exact:true})).toBeVisible();
  for(const entry of [
    {section:"Istoric medical",field:"Titlu",value:"Observație fictivă"},
    {section:"Alergii",field:"Substanță sau alergen",value:"Alergen fictiv"},
    {section:"Vaccinări",field:"Numele vaccinului",value:"Vaccin fictiv"},
    {section:"Contacte de urgență",field:"Numele persoanei",value:"Persoană fictivă"},
  ]) {
    await page.getByRole("button",{name:entry.section,exact:true}).click();
    await page.getByRole("button",{name:"Adaugă înregistrare"}).click();
    await page.getByLabel(entry.field,{exact:false}).fill(entry.value);
    if(entry.section==="Contacte de urgență") {
      await page.getByLabel("Telefon de contact").fill("0000000000");
      await page.getByLabel("Relația cu persoana").fill("Prieten");
    }
    await expect(page.getByRole("button",{name:"Istoric medical",exact:true})).toBeDisabled();
    await page.getByRole("button",{name:"Salvează înregistrarea"}).click();
    await expect(page.getByRole("heading",{name:entry.value,exact:true})).toBeVisible();
    if(entry.section==="Contacte de urgență") {
      await expect(page.getByText("0000000000",{exact:true})).toBeVisible();
      await expect(page.getByText("Prieten",{exact:true})).toBeVisible();
    }
    await page.getByRole("button",{name:"Editează",exact:true}).click();
    await page.getByLabel(entry.field,{exact:false}).fill(entry.value+" corectată");
    await page.getByRole("button",{name:"Salvează înregistrarea"}).click();
    await expect(page.getByRole("heading",{name:entry.value+" corectată",exact:true})).toBeVisible();
    if(entry.section==="Istoric medical") {
      await page.locator("main").evaluate(el=>{el.scrollTop=0;});
      await page.screenshot({path:`../docs/screenshots/record-${info.project.name}.png`,fullPage:true,animations:"disabled"});
      await page.getByRole("button",{name:"Comută tema"}).click();
      await expect(page.locator("html")).toHaveClass(/dark/);
      await page.screenshot({path:`../docs/screenshots/record-dark-${info.project.name}.png`,fullPage:true,animations:"disabled"});
    }
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    await page.getByRole("button",{name:"Șterge",exact:true}).click();
    await page.getByRole("button",{name:"Păstrează înregistrarea"}).click();
    await expect(page.getByRole("heading",{name:entry.value+" corectată",exact:true})).toBeVisible();
    await page.getByRole("button",{name:"Șterge",exact:true}).click();
    await page.getByRole("button",{name:"Confirmă ștergerea",exact:true}).click();
    await expect(page.getByText("Nicio înregistrare încă",{exact:true})).toBeVisible();
  }
  await page.goto("/settings");
  await page.getByRole("button",{name:"Șterge contul",exact:true}).click();
  await page.getByPlaceholder("Parola",{exact:true}).fill("Testing-pass-123!");
  await page.getByRole("button",{name:"Confirmă ștergerea",exact:true}).click();
  await expect(page).toHaveURL(/login\?deleted=complete/);
  expect(errors).toEqual([]);
});

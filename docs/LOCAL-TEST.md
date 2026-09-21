# Versiune locală de test — 21 septembrie 2026

Folosește exclusiv date fictive. Această versiune nu este o lansare medicală publică.

## Pornire Windows

Cerințe: Python 3.11+, Node.js 22, npm și PowerShell. Din rădăcina repository-ului:

```powershell
python -m venv .venv
.\RUN_LOCAL.ps1 -Python "$PWD\.venv\Scripts\python.exe"
```

La pornirile următoare adaugă `-SkipInstall`. Scriptul aplică migrarea Alembic, construiește frontendul și pornește procese ascunse. Refuză porturile ocupate, fără a opri alte aplicații.

- Interfață: http://localhost:3012/register
- API: http://localhost:8012/docs
- Documente fictive pentru upload: `demo/analize-fictive.pdf` și `demo/analize-fictive.docx`.

Contul se creează în interfață. Confirmarea emailului și recuperarea parolei folosesc fișierele din `.local-data/mailbox`: deschide cel mai recent mesaj destinat adresei fictive și copiază linkul în browser. Mesajele nu sunt trimise extern. Nu publica acest director.

Cheile generate o singură dată, baza SQLite, originalele criptate, emailurile și jurnalele sunt în `.local-data`, exclus din Git. Păstrează directorul și cheile între reporniri; pierderea cheii face originalele criptate inaccesibile. ID-urile proceselor sunt în `processes.json`; verifică procesele și oprește numai instanța 8012/3012 înainte de repornire. Datele nu se șterg la oprire.

## Configurație și limite

`STORAGE_BACKEND=local` este permis numai în dezvoltare. `LOCAL_DATA_DIR` indică directorul privat. `STORAGE_BACKEND=s3` rămâne implicit și obligatoriu în producție; configurația S3 existentă rămâne în uz. Originalele se descarcă prin `GET /api/v1/documents/{id}/original`, cu autentificare și verificarea proprietarului. Ruta veche de link S3 nu produce URL-uri publice pentru stocarea locală.

Recuperarea folosește tokenuri aleatoare, stocate doar ca hash, cu scop, expirare și consum atomic. Migrarea `f6b8d0a2c4e6` invalidează implicit vechile linkuri JWT; solicită un link nou. Resetarea revocă sesiunile existente. Fără `SMTP_HOST`, recuperarea în producție întoarce uniform 503. Pentru email real sunt necesare `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` și un `FRONTEND_URL` HTTPS corect; vezi și setările backend. Nu pune parole în Git.

AI rulează cu `AI_DEFAULT_PROVIDER=mock`, iar interfața afișează permanent modul de test. OCR real și SMTP/S3 reale și notificările externe nu au fost validate în acest increment. Webul local folosește cookie-uri HttpOnly prin aceeași origine. Exportul mobil utilizează tokenuri bearer păstrate prin Keychain/Android Keystore; verificarea pe dispozitive fizice rămâne necesară.

## Verificări repetabile

```powershell
# Din backend, folosind mediul virtual
python -m ruff check .
python -m pytest -q
# Din frontend, cu aplicația locală pornită
npm.cmd run lint
npm.cmd run test:unit
npm.cmd run test:e2e
npm.cmd audit --omit=dev
```

Pentru exportul Capacitor, oprește frontendul înainte de build și setează `NEXT_PUBLIC_API_URL` la adresa API accesibilă dispozitivului, apoi `npm.cmd run build:mobile`. Exportul web nu înseamnă APK/IPA sau test pe dispozitiv fizic. Rulează din nou scriptul local pentru revenirea la buildul web.

CI verifică backend, TypeScript, sesiuni, browser și exportul mobil. Hookurile Render sunt limitate la push pe `claude/new-isolated-project-oheqvr`; ramura de lucru și PR-ul nu declanșează aceste hookuri. Acest increment nu modifică Render și nu se îmbină automat în ramura de lansare.

## Sesiuni web HttpOnly

Scriptul local setează `NEXT_PUBLIC_SESSION_TRANSPORT=cookie` și `BACKEND_URL=http://localhost:8012`. Cererile browserului merg la `/api/v1` pe aceeași origine; Next transmite cererile server-side către API. Backendul emite cookie-uri HttpOnly, SameSite=Lax, cu Secure în producție, fără Domain explicit. `FRONTEND_URL` trebuie să fie originea exactă a interfeței (fără cale); cererile de autentificare/reînnoire și modificările autentificate prin cookie sunt respinse dacă Origin lipsește sau diferă. API-ul bearer pentru clienți nativi este păstrat.

Pentru activare pe un mediu web viitor: setează variabila publică înainte de build, `BACKEND_URL` la serviciul API accesibil serverului și `FRONTEND_URL` la originea HTTPS reală. Nu este necesară expunerea adresei interne în browser. Nicio configurație Render nu a fost schimbată aici. Exportul mobil forțează explicit transportul native și exclude proxy-ul serverului Next.

La migrare, copia veche a tokenurilor din localStorage este eliminată și utilizatorul se autentifică din nou. Dacă serverul nu confirmă logoutul, interfața avertizează explicit că unele sesiuni pot rămâne active. Ștergerea cookie-urilor locale nu este raportată ca revocare pe toate dispozitivele.

## DOCX și reprocesare

DOCX este acceptat cu text din paragrafe și tabele, fără OCR extern. Arhivele sunt verificate înainte de stocare: maximum 2.000 de intrări și 25 MB decomprimat; criptarea ZIP, expansiunea excesivă și declarațiile XML DTD/ENTITY sunt respinse. Clasificarea automată ca analize se aplică numai categoriei Altele și numai când sunt extrase valori de laborator.

Lipsa textului sau o eroare de procesare produce starea „Necesită verificare”, păstrând originalul. Reprocesarea înlocuiește valorile într-o tranzacție numai după succes; la eșec păstrează rezultatele anterioare. Două procesări ale aceluiași document nu rulează simultan. După o întrerupere, procesarea poate fi reluată manual după expirarea rezervării de 20 de minute; identificatorul încercării împiedică suprascrierea de către un proces vechi. Reluarea automată în fundal rămâne de implementat.

## Acord AI

Setări afișează furnizorul activ și permite acordul/retragerea. Providerul mock rămâne local; dacă `REQUIRE_AI_CONSENT=true`, și simularea cere acord. Orice provider diferit de mock cere acord chiar dacă această variabilă este false. Acordul este legat de versiunea politicii și numele furnizorului; acordurile vechi generice nu autorizează procesarea externă. Schimbarea furnizorului cere reconfirmare. Retragerea oprește cererile viitoare, nu apelurile deja începute și nu șterge automat date la furnizori. Înainte de activarea externă sunt necesare politica de confidențialitate, condițiile furnizorului și configurarea retenției.

## Ștergere și curățare persistentă

Ștergerea contului elimină datele relaționale și înregistrează, în aceeași tranzacție, operațiile de ștergere a originalelor. Cheile obiectelor din coadă sunt criptate. Codul 204 confirmă terminarea; 202 indică ștergerea originalelor încă în curs. În dezvoltare sunt eliminate și emailurile locale ale contului. Jurnalul de audit de securitate rămâne separat, cu legătura către utilizator eliminată.

Procesul integrat reîncearcă la 30 de secunde (`STORAGE_CLEANUP_ENABLED=true`, `STORAGE_CLEANUP_INTERVAL_SECONDS=30`), inclusiv după repornire. O operație rezervată de un proces întrerupt poate fi reluată după două minute. Administratorul poate verifica numărul și vechimea operațiilor prin `GET /api/v1/admin/storage-cleanup`, fără expunerea cheilor sau numelor de fișiere. Nu schimba backendul de stocare și nu roti cheia de criptare cât timp coada are operații nefinalizate.

Limite externe: copii de siguranță, emailuri deja trimise prin SMTP și versiuni istorice/Object Lock din S3 necesită politici separate de retenție și verificare înainte de lansare. S3 DeleteObject nu garantează eliminarea versiunilor istorice. Date orfane provenite din versiuni vechi cu cheile externe SQLite dezactivate necesită audit separat; noua configurare activează relațiile pentru operațiile viitoare.

## Teste browser extinse

Pentru suita automată cu multe conturi fictive, pornește temporar cu `RUN_LOCAL.ps1 -TestTraffic` (plus calea Python și `-SkipInstall`, dacă mediul este instalat). Acest mod dezactivează doar limita de autentificări în instanța locală de dezvoltare. După teste, repornește fără `-TestTraffic`; limita este reactivată. CI utilizează aceeași separare; protecția este verificată separat în testele backend.


## Corectarea analizelor

Secțiunea Analize permite adăugarea, corectarea și ștergerea confirmată a rezultatelor. Introdu valoarea, unitatea, intervalul și data din documentul sursă; confirmarea transcrierii nu este validare medicală. Corectarea păstrează originalul și legătura cu documentul, invalidează explicațiile AI vechi și actualizează graficele. Reprocesarea documentului înlocuiește corecturile manuale ale rezultatelor sale. În timpul procesării, modificările acestor rezultate sunt blocate temporar.

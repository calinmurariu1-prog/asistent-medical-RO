# Asistent Medical RO — raport de livrare locală

Stare verificată la 21 septembrie 2026. Repository `calinmurariu1-prog/asistent-medical-RO`, ramură `codex/medical-launch-readiness`, [PR draft #21](https://github.com/calinmurariu1-prog/asistent-medical-RO/pull/21). Codul aplicației verificat: `94921e6`.

Aplicația este o versiune locală de test cu date fictive și AI simulat. Nu este declarată pregătită pentru pacienți reali. Publicarea ramurii actualizează PR-ul; nu produce lansarea pe Render.

## Funcții disponibile

| Zonă | Comportament implementat |
| --- | --- |
| Cont și sesiuni | Înregistrare/login, confirmare email, recuperare parolă cu tokenuri opace consumate atomic, revocare sesiuni după resetare, configurare MFA, coduri de rezervă de unică folosință și regenerare cu parolă plus al doilea factor, limitarea încercărilor, refresh unic pentru cereri simultane și logout pe toate dispozitivele. |
| Web și mobil | Next.js/FastAPI păstrate, web responsive, dark mode, PWA și export Capacitor. Web: cookie HttpOnly și verificare Origin; nativ: Keychain/Keystore fără fallback necriptat. |
| Profil și dosar | Profil cu nume, naștere, sex, greutate, înălțime, telefon și grupă sanguină declarată; erori recuperabile, validare și audit fără valori personale; istoric/observații/diagnostice consemnate, alergii, vaccinări și contacte de urgență cu creare, corectare și ștergere confirmată. |
| Documente | PDF/JPG/PNG/DOCX/DICOM, păstrarea originalului, extragere disponibilă, erori explicite când OCR lipsește, limite de fișier și arhivă DOCX. Descărcare autentificată numai de proprietar. |
| Analize | Parser, verificarea concordanței valorii/unității/intervalului, corectare manuală auditată, data documentului propagată, istoric și grafice. Valorile neconfirmate și seriile cu unități/date incompatibile sunt excluse din interpretare/comparație. |
| Medicație | Tratament transcris, doză/frecvență/instrucțiuni/perioadă/note, activ/istoric, editare și ștergere. Memento-uri zilnice explicite, maximum 12 per tratament, cu fus IANA, pauză/reactivare și reguli documentate pentru ora de vară. |
| Programări și notificări | Creare/reprogramare/anulare/ștergere, memento înaintea consultației, inbox necitite/viitoare/toate, citire și ștergere. Worker cu rezervări, reluare și reîncercări persistente. |
| Export | PDF/Word, JSON și arhivă ZIP cu originale; JSON cu profil, acorduri, dosar, documente extrase, analize, medicație, memento-uri, programări, conversații, contacte, date/dispozitive de sănătate, notificări, feedback, starea abonamentului și evenimentele proprii de audit. |
| Ștergere și stocare | Originale locale criptate, intenții persistente de curățare după ștergere sau upload întrerupt, reîncercări după repornire, ștergere cont cu cascadare și eliminarea emailurilor locale. |

## Securitate și limite operaționale

MFA folosește chei TOTP criptate; o configurare nu poate înlocui un secret activ. Activarea revocă sesiunile și afișează o singură dată 10 coduri de rezervă de 128 biți. Baza de date păstrează numai hashurile SHA-256; consumul este atomic și cere și parola. Regenerarea din Setări cere parola și TOTP sau un cod de rezervă valid, invalidează setul anterior și revocă sesiunile. Nu există recuperare fără niciun al doilea factor sau cod păstrat.

Logout-all incrementează atomic versiunea sesiunilor din baza de date. Răspunsurile API au `no-store`, inclusiv datele medicale, tokenurile și erorile de validare. Limitarea cererilor este sincronizată între fire, elimină istoricul expirat și are maximum 10.000 chei per proces; la capacitate refuză cereri noi. Scalarea la mai multe procese/instanțe necesită un mecanism distribuit.

Workerul de curățare elimină cel mult 500 hashuri de resetare/confirmare expirate per ciclu, după încă `RECOVERY_TOKEN_RETENTION_HOURS` (implicit 24). Nu elimină coduri MFA, audit sau date clinice. Retenția documentelor, emailurilor locale și backupurilor are cerințe separate.

Accesarea originalelor, emiterea unui link și ștergerea sunt auditate cu identificatori, fără numele fișierului sau conținut. Ștergerea și auditul ei se salvează împreună. Citirea S3 închide fluxul și la eroare; originalul lipsă produce 404, indisponibilitatea produce 503 fără detalii interne.

Arhiva ZIP se construiește în memorie, fără fișier temporar necriptat pe server, și conține `dosar.json` plus originale cu nume bazate pe ID. Inventarul păstrează numele original, tipul, dimensiunea și SHA-256. Lipsa unui original oprește întregul export. Limita este 25 MB/1000 documente și 2 cereri/minut/IP pe instanță; pentru dosare mai mari se folosesc exportul JSON și descărcările individuale.

## AI: comportament și limite

- Chatul caută în documentele proprietarului, cere identificatori de citare disponibili și se abține fără surse relevante. Verificarea identificatorului nu dovedește că sursa susține semantic fiecare afirmație.
- Rezumatele dosarului și comparațiile citează înregistrările utilizatorului, declară limita de 20 de înregistrări pe categorie și nu transformă variația numerică în diagnostic. Explicațiile analizelor se bazează pe valoarea și intervalul înregistrat; o corectare concurentă împiedică salvarea unei explicații învechite.
- Explicațiile medicamentelor și verificarea ingredientelor folosesc un catalog educațional limitat cu surse NHS/NHS SPS. Nu se deduc ingrediente din denumiri comerciale și lipsa unei potriviri nu este prezentată ca siguranță demonstrată.
- Cele șase funcții educaționale folosesc surse limitate, textul utilizatorului etichetat sau întrebări deterministe. Subiectele fără acoperire se abțin. Modul simulat este vizibil.
- Routerul local recunoaște un set limitat de semnale de alarmă înainte de inițializarea furnizorului AI și oferă îndrumare condiționată către 112. Nu este triaj clinic validat.
- Apelurile externe cer acord explicit pentru furnizorul curent. Niciun rezultat nu reprezintă validare de medic, diagnostic sau prescripție autonomă. Evaluarea clinică rămâne obligatorie înainte de lansare.

## Fișiere și livrare pe mobil

Exporturile ZIP/JSON/PDF/DOCX și originalele folosesc descărcarea web sau dialogul nativ de partajare. Copia nativă are nume generic și se află în cache-ul privat; Android FileProvider expune numai subdirectorul dedicat. Copiile mai vechi de 24 de ore se curăță la următorul export, fără promisiune de ștergere la un termen exact când aplicația este închisă. Limita nativă este 25 MB. Închiderea dialogului nu dovedește salvarea la destinație.

Push-ul simulat nu marchează livrare reală. Acceptarea de FCM/APNs nu dovedește afișarea pe telefon. O întrerupere după acceptarea furnizorului poate produce duplicate; livrarea separată pe fiecare dispozitiv nu este urmărită. Memento-urile medicale prea întârziate nu sunt expediate ca recomandare de recuperare a dozei.

## Dovezi de verificare

- Verificarea integrată locală pentru `94921e6`: 302 teste backend trecute, 5 teste PostgreSQL omise local; toate cele 39 scenarii browser trecute. Aplicația a fost repornită cu limitările normale.
- Cele 14 teste unitare frontend au trecut; buildul Next/TypeScript a produs 38 pagini.
- Ultimul CI complet confirmat: [fd038a1](https://github.com/calinmurariu1-prog/asistent-medical-RO/actions/runs/35632622113), inclusiv PostgreSQL, migrații, concordanța schemei, backend, browser și audit de dependențe.
- APK debug: [3ddfe17](https://github.com/calinmurariu1-prog/asistent-medical-RO/actions/runs/35632844280) trecut. Ultima modificare ulterioară a codului aplicației afectează antetele backend. CI pentru `94921e6` era în curs la verificare.
- Capturile arată randarea desktop/iPhone/Android; scenariile Playwright folosesc dimensiuni de browser, fără dispozitive fizice. Nu există dovadă de build/semnare IPA sau testare fizică iOS.
- S3 este simulat în teste. Testele locale omit explicit cazurile care necesită PostgreSQL; aceste cazuri rulează separat în GitHub Actions.

## Restanțe pentru produs și lansare

1. Configurare și verificare externă PostgreSQL de producție, S3, SMTP, OCR real, furnizor AI, FCM/APNs; cheile rămân în variabile de mediu. Emailurile locale și simularea nu înlocuiesc aceste servicii.
2. Evaluare medicală independentă a surselor, citărilor, regulilor de alarmă și rezultatelor AI; acoperirea actuală este limitată.
3. Testare fizică Android/iOS: sesiuni, descărcare/partajare, push, PWA, accesibilitate și integrarea datelor de sănătate. iOS necesită macOS/Xcode, manifest de confidențialitate integrat și semnare.
4. Exportul nu este încă un pachet integral: facturile externe nu sunt incluse. CNP-ul poate fi inclus opțional în JSON prin reconfirmarea parolei și a celui de-al doilea factor când MFA este activ; ZIP rămâne fără CNP. Arhiva ZIP cu JSON și originale este disponibilă până la 25 MB și 1000 documente; exporturile mai mari necesită descărcări separate. Starea abonamentului local este inclusă; identificatorii furnizorului sunt excluși deoarece pot reprezenta tokenuri de cumpărare. Detaliile interne libere de audit și secretele de autentificare sunt excluse explicit. Exportul nu este o certificare GDPR.
5. Politici externe de retenție, backup, S3 versioning/Object Lock, restaurare și ștergere verificată. Intenția de curățare nu constituie atomicitate distribuită cu S3; scrierile externe foarte întârziate necesită reconciliere.
6. Recurențe de medicație mai complexe decât ore zilnice și evidența administrării; niciun orar nu se deduce automat din doză. Canalele de notificare email/SMS nu sunt implementate complet.
7. Verificarea documentelor contractuale și a politicilor de confidențialitate, limitelor operaționale și monitorizării înainte de date reale.

## Rulare și documentație

- [Pornire locală și servicii simulate](LOCAL-TEST.md): `RUN_LOCAL.ps1`, API `8012`, interfață `3012`, SQLite și chei persistente în `.local-data` exclus din Git. Aplicația veche pe `8000` rămâne separată.
- [Configurare și limite mobile](MOBILE.md): Capacitor, Android, iOS, exporturi și cerințe externe.
- Migrațiile Alembic și verificarea PostgreSQL rulează în CI. Pentru publicare, se verifică rezultatele **reviziei exacte** din PR; rezultatele unui commit anterior nu certifică următorul.

În acest increment nu au fost schimbate servicii Render, activate servicii plătite, folosite date medicale reale sau efectuat merge în ramura de lansare.

Export identificator: POST /gdpr/export/with-identifier cere include_cnp explicit, parola și MFA/TOTP sau cod de rezervă valid dacă MFA este activ. Codul de rezervă se consumă atomic; auditul nu conține identificatorul sau parolele. Dacă decriptarea eșuează, exportul este refuzat. 11 teste export/GDPR și 3 scenarii browser trecute, plus Ruff și build/TypeScript.

Erori de validare: handlerul API păstrează numai loc/type/msg și elimină input/context, inclusiv pentru parole, MFA, CNP și JSON invalid. Cele 12 teste securitate/profil/export sensibil au trecut; Ruff trecut.

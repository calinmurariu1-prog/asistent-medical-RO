# Asistent Medical RO — raport de livrare locală

Stare verificată la 21 septembrie 2026. Repository `calinmurariu1-prog/asistent-medical-RO`, ramură `codex/medical-launch-readiness`, [PR draft #21](https://github.com/calinmurariu1-prog/asistent-medical-RO/pull/21). Codul aplicației verificat: `f3345d4`.

Aplicația este o versiune locală de test cu date fictive și AI simulat. Nu este declarată pregătită pentru pacienți reali. Publicarea ramurii actualizează PR-ul; nu produce lansarea pe Render.

## Funcții disponibile

| Zonă | Comportament implementat |
| --- | --- |
| Cont și sesiuni | Înregistrare/login, confirmare email, recuperare parolă cu tokenuri opace consumate atomic, revocare sesiuni după resetare, MFA la autentificare, limitarea încercărilor, refresh unic pentru cereri simultane și logout pe toate dispozitivele. |
| Web și mobil | Next.js/FastAPI păstrate, web responsive, dark mode, PWA și export Capacitor. Web: cookie HttpOnly și verificare Origin; nativ: Keychain/Keystore fără fallback necriptat. |
| Profil și dosar | Profil cu erori recuperabile, validare și audit fără valori personale; istoric/observații/diagnostice consemnate, alergii, vaccinări și contacte de urgență cu creare, corectare și ștergere confirmată. |
| Documente | PDF/JPG/PNG/DOCX/DICOM, păstrarea originalului, extragere disponibilă, erori explicite când OCR lipsește, limite de fișier și arhivă DOCX. Descărcare autentificată numai de proprietar. |
| Analize | Parser, verificarea concordanței valorii/unității/intervalului, corectare manuală auditată, data documentului propagată, istoric și grafice. Valorile neconfirmate și seriile cu unități/date incompatibile sunt excluse din interpretare/comparație. |
| Medicație | Tratament transcris, doză/frecvență/instrucțiuni/perioadă/note, activ/istoric, editare și ștergere. Memento-uri zilnice explicite, maximum 12 per tratament, cu fus IANA, pauză/reactivare și reguli documentate pentru ora de vară. |
| Programări și notificări | Creare/reprogramare/anulare/ștergere, memento înaintea consultației, inbox necitite/viitoare/toate, citire și ștergere. Worker cu rezervări, reluare și reîncercări persistente. |
| Export | PDF/Word și JSON cu profil, acorduri, dosar, documente extrase, analize, medicație, memento-uri, programări, conversații, contacte, date/dispozitive de sănătate, notificări, feedback, starea abonamentului și evenimentele proprii de audit. |
| Ștergere și stocare | Originale locale criptate, intenții persistente de curățare după ștergere sau upload întrerupt, reîncercări după repornire, ștergere cont cu cascadare și eliminarea emailurilor locale. |

## AI: comportament și limite

- Chatul caută în documentele proprietarului, cere identificatori de citare disponibili și se abține fără surse relevante. Verificarea identificatorului nu dovedește că sursa susține semantic fiecare afirmație.
- Rezumatele dosarului și comparațiile citează înregistrările utilizatorului, declară limita de 20 de înregistrări pe categorie și nu transformă variația numerică în diagnostic. Explicațiile analizelor se bazează pe valoarea și intervalul înregistrat; o corectare concurentă împiedică salvarea unei explicații învechite.
- Explicațiile medicamentelor și verificarea ingredientelor folosesc un catalog educațional limitat cu surse NHS/NHS SPS. Nu se deduc ingrediente din denumiri comerciale și lipsa unei potriviri nu este prezentată ca siguranță demonstrată.
- Cele șase funcții educaționale folosesc surse limitate, textul utilizatorului etichetat sau întrebări deterministe. Subiectele fără acoperire se abțin. Modul simulat este vizibil.
- Routerul local recunoaște un set limitat de semnale de alarmă înainte de inițializarea furnizorului AI și oferă îndrumare condiționată către 112. Nu este triaj clinic validat.
- Apelurile externe cer acord explicit pentru furnizorul curent. Niciun rezultat nu reprezintă validare de medic, diagnostic sau prescripție autonomă. Evaluarea clinică rămâne obligatorie înainte de lansare.

## Fișiere și livrare pe mobil

Exporturile JSON/PDF/DOCX și originalele folosesc descărcarea web sau dialogul nativ de partajare. Copia nativă are nume generic și se află în cache-ul privat; Android FileProvider expune numai subdirectorul dedicat. Copiile mai vechi de 24 de ore se curăță la următorul export, fără promisiune de ștergere la un termen exact când aplicația este închisă. Limita nativă este 25 MB. Închiderea dialogului nu dovedește salvarea la destinație.

Push-ul simulat nu marchează livrare reală. Acceptarea de FCM/APNs nu dovedește afișarea pe telefon. O întrerupere după acceptarea furnizorului poate produce duplicate; livrarea separată pe fiecare dispozitiv nu este urmărită. Memento-urile medicale prea întârziate nu sunt expediate ca recomandare de recuperare a dozei.

## Dovezi de verificare

- Verificare integrată locală pentru `f3345d4`: 276 teste backend trecute, 4 omise local deoarece necesită PostgreSQL; toate cele 36 scenarii browser trecute.
- Cele 13 teste unitare de sesiune/export au trecut; buildul Next/TypeScript a produs 38 de pagini.
- Ultimul CI complet confirmat: [f3345d4](https://github.com/calinmurariu1-prog/asistent-medical-RO/actions/runs/35628191180), inclusiv PostgreSQL, migrații, concordanța schemei, backend, browser și audit de dependențe.
- APK debug pentru codul `f3345d4`: [build trecut](https://github.com/calinmurariu1-prog/asistent-medical-RO/actions/runs/35628187833). CI complet al aceleiași revizii a trecut.
- Capturile din `docs/screenshots` demonstrează randarea la dimensiuni desktop/iPhone/Android; nu demonstrează funcționarea pe dispozitive fizice.
- Nu există dovadă de build/semnare IPA sau testare fizică iOS. Exportul static Capacitor și sincronizarea Android au trecut în incrementul adaptorului nativ; verificarea APK se face în GitHub Actions.

## Restanțe pentru produs și lansare

1. Configurare și verificare externă PostgreSQL de producție, S3, SMTP, OCR real, furnizor AI, FCM/APNs; cheile rămân în variabile de mediu. Emailurile locale și simularea nu înlocuiesc aceste servicii.
2. Evaluare medicală independentă a surselor, citărilor, regulilor de alarmă și rezultatelor AI; acoperirea actuală este limitată.
3. Testare fizică Android/iOS: sesiuni, descărcare/partajare, push, PWA, accesibilitate și integrarea datelor de sănătate. iOS necesită macOS/Xcode, manifest de confidențialitate integrat și semnare.
4. Exportul nu este încă un pachet integral: lipsesc CNP și facturile externe. Arhiva ZIP cu JSON și originale este disponibilă până la 25 MB și 1000 documente; exporturile mai mari necesită descărcări separate. Starea abonamentului local este inclusă; identificatorii furnizorului sunt excluși deoarece pot reprezenta tokenuri de cumpărare. Detaliile interne libere de audit și secretele de autentificare sunt excluse explicit. Exportul nu este o certificare GDPR.
5. Politici externe de retenție, backup, S3 versioning/Object Lock, restaurare și ștergere verificată. Intenția de curățare nu constituie atomicitate distribuită cu S3; scrierile externe foarte întârziate necesită reconciliere.
6. Recurențe de medicație mai complexe decât ore zilnice și evidența administrării; niciun orar nu se deduce automat din doză. Canalele de notificare email/SMS nu sunt implementate complet.
7. Verificarea documentelor contractuale și a politicilor de confidențialitate, limitelor operaționale și monitorizării înainte de date reale.

## Rulare și documentație

- [Pornire locală și servicii simulate](LOCAL-TEST.md): `RUN_LOCAL.ps1`, API `8012`, interfață `3012`, SQLite și chei persistente în `.local-data` exclus din Git. Aplicația veche pe `8000` rămâne separată.
- [Configurare și limite mobile](MOBILE.md): Capacitor, Android, iOS, exporturi și cerințe externe.
- Migrațiile Alembic și verificarea PostgreSQL rulează în CI. Pentru publicare, se verifică rezultatele **reviziei exacte** din PR; rezultatele unui commit anterior nu certifică următorul.

În acest increment nu au fost schimbate servicii Render, activate servicii plătite, folosite date medicale reale sau efectuat merge în ramura de lansare.

Increment export abonament: 9 teste GDPR trecute, inclusiv izolare între conturi, cont fără pacient și excluderea identificatorilor furnizorului.

Descărcarea originalelor: 25 teste documente/stocare trecute. Fluxul S3 este închis inclusiv după citire eșuată; fișierul lipsă produce 404, iar erorile de citire produc 503 cu mesaj fără detalii interne și fără cache. Verificarea S3 folosește un client simulat, nu un serviciu extern.

Audit documente: accesul autorizat la original, emiterea unui link și ștergerea sunt consemnate cu ID-ul documentului și utilizatorului, fără nume/conținut. Evenimentul de acces nu dovedește salvarea fișierului pe dispozitiv. Ștergerea și auditul sunt comise împreună. Cele 25 teste documente/curățare au trecut, inclusiv verificarea accesului altui cont și exportarea evenimentului de ștergere.

MFA: configurarea nu poate înlocui un secret activ; activarea verifică atomic aceeași configurare și revocă sesiunile anterioare. Configurarea/activarea au limitare de cereri și audit fără secret. Suita autentificare/sesiuni/recuperare a trecut (28 teste, un test PostgreSQL omis local), apoi toate cele 7 teste auth au trecut după adăugarea cazului de configurare schimbată în timpul verificării. Configurarea MFA este disponibilă în Setări, cu cheie TOTP manuală, confirmarea păstrării cheii și cod înainte de activare. Activările noi primesc 10 coduri de rezervă de unică folosință, afișate o singură dată. Conturile deja activate pot genera un set nou din Setări, cu parola și TOTP sau cod de rezervă valid; setul anterior și sesiunile sunt invalidate.

Interfață MFA: 3 scenarii browser trecute (desktop/iPhone/Android), incluzând activare, reautentificare cu cod, persistența stării și ștergerea contului fictiv. Build Next/TypeScript trecut, 38 pagini. Aplicația locală repornită cu limitările normale.

Recuperare MFA: migrare c5e7a9b1d3f6 aplicată local; 10 teste auth/recuperare trecute, un test concurent PostgreSQL rezervat CI. Coduri de 128 biți păstrate doar ca SHA-256, consum atomic legat de proprietar și parolă, revocarea sesiunilor anterioare, excludere din export și ștergere cu contul. Răspunsurile cu secrete au no-store. Trei scenarii browser de activare și autentificare cu un cod de rezervă au trecut; build Next/TypeScript trecut.

Regenerare coduri MFA: 11 teste auth/recuperare trecute și un test PostgreSQL omis local; 3 scenarii browser trecute cu regenerare și autentificare folosind un cod nou. Build/TypeScript trecut. CI complet pentru c934359 a trecut (run 35630345056); APK pentru 5190e79 a trecut (run 35630832948), iar CI acelei revizii era încă în curs la verificare.

Revocare sesiuni: logout-all incrementează atomic versiunea din baza de date și consemnează evenimentul fără date sensibile. 15 teste auth/sesiuni browser trecute, inclusiv un cont încărcat cu o versiune veche. Pentru 5190e79, toate joburile CI din run 35630839288 sunt confirmate trecute (PostgreSQL/migrații, backend, frontend/browser și audit); deploy Render omis.

Arhivă dosar: GET /gdpr/export/archive, proprietar autentificat, ZIP în memorie fără fișiere temporare, dosar.json și originale cu nume bazate pe ID, inventar SHA-256 și tip/nume original. Un original indisponibil oprește întregul export cu 503; dimensiunea reală se verifică independent de metadate. Limită 25 MB/1000 documente, 2 cereri/minut/IP pe instanță. Trei teste backend de izolare/integritate/limite și trei scenarii browser export au trecut, plus Ruff și build/TypeScript.

Limitare cereri: operația de verificare/adăugare este protejată între firele de execuție, istoricul expirat este eliminat periodic, maximum 10.000 de chei IP/rută/fereastră per proces. La capacitate refuză cereri noi fără a șterge istoricul activ. Răspunsul 429 include Retry-After și no-store. 19 teste securitate/autentificare/limitare trecute, inclusiv 12 cereri simultane pentru o limită de 3. Un backend distribuit rămâne necesar înainte de scalarea la mai multe procese/instanțe.

Retenție tehnică: workerul existent curăță în loturi de 500 amprentele tokenurilor resetare/confirmare după expirare plus RECOVERY_TOKEN_RETENTION_HOURS (implicit 24). Nu atinge coduri MFA, audit sau date clinice. 13 teste recuperare/curățare trecute și un test PostgreSQL omis local; Ruff trecut.

Profil: telefonul și grupa sanguină pot fi completate, modificate și eliminate din interfață; câmpurile goale sunt trimise ca null. Grupa este etichetată ca informație declarată, fără confirmare medicală. Trei scenarii browser (desktop/iPhone/Android) au trecut pentru salvare, păstrare după reîncărcare și ștergere, fără depășire orizontală; build/TypeScript trecut.

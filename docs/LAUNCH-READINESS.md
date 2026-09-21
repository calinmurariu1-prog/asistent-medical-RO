# Raport pentru versiunea locală — 21 septembrie 2026

Repository: calinmurariu1-prog/asistent-medical-RO. Livrare pe `codex/medical-launch-readiness`, PR #21. Vezi [instrucțiunile locale](LOCAL-TEST.md).

## Implementat

- Analizele fără interval/valoare numerică sunt neevaluabile; nu se deduc praguri critice generice. Graficele/comparațiile sunt blocate pentru unități incompatibile sau cronologie incertă; migrarea elimină clasificările și explicațiile vechi.
- Acord AI explicit în Setări, legat de furnizor; obligatoriu înaintea tuturor apelurilor către AI extern, cu retragere și verificare pe server.
- Ștergere cont/document cu curățarea persistentă și reîncercarea originalelor; status explicit pentru fișiere în curs, emailuri locale eliminate și relații SQLite active.
- Dosar medical în interfață: istoric/observații, alergii și vaccinări cu creare/editare/ștergere confirmată, validare și audit fără text medical.
- Data documentului la upload și corectare ulterioară; cronologia analizelor se actualizează, explicațiile vechi sunt invalidate, iar dashboardul numără separat rezultatele neevaluabile.
- Loginul Swagger aplică verificările pentru cont activ, MFA, audit și limitarea încercărilor.
- Recuperare parolă și confirmare email în română; tokenuri opace, hash în DB, expirare, scop și consum atomic. Resetarea revocă sesiunile.
- Emailuri private pe disc în dezvoltare, fără tokenuri în loguri/răspunsuri. Recuperare indisponibilă uniform în producție fără SMTP.
- Stocare nativă Keychain/Keystore, fără fallback necriptat, iCloud oprit și backup Android dezactivat.
- Sesiuni web HttpOnly prin proxy de aceeași origine, protecție Origin pentru cererile cu cookie și eliminarea tokenurilor web din localStorage.
- Refresh automat unic pentru cereri simultane, maximum o reluare; logout pe toate dispozitivele și avertizare la revocare neconfirmată.
- DOCX cu paragrafe/tabele și validarea arhivei; fără succes fictiv când OCR nu extrage text. Reprocesarea păstrează rezultatele vechi până la succes.
- Originale locale criptate, persistente, descărcate autentificat cu verificarea proprietarului; încărcare limitată ca dimensiune.
- Next.js 16.3.5, React 19, compatibilitate export Capacitor; interfața existentă păstrată și antet mobil corectat.
- Pornire separată 8012/3012, SQLite și chei persistente; PDF fictiv și banner AI simulat.
- CI pentru toate verificările și hookuri Render limitate la ramura de lansare.

## Dovezi locale

- Backend: 208 teste trecute, inclusiv consum concurent, token expirat/reutilizat/scop greșit, autentificare, MFA, sesiuni și acces documente între utilizatori.
- Ruff trecut; build Next și TypeScript trecute; zece teste unitare pentru refresh/concurență trecute.
- Export web Capacitor: 37 pagini construite. Nu au fost testate dispozitive fizice și nu s-au produs APK/IPA semnate.
- Verificările browser acoperă cont, confirmare, profil, PDF, descărcare identică, analize, dashboard, refresh, resetare și deconectare pe desktop și dimensiuni iPhone/Android. Capturi în `docs/screenshots`.
- Auditul npm complet (inclusiv dezvoltare): zero vulnerabilități raportate după actualizarea Capacitor 8.5.2 și a dependențelor indirecte. Generarea iconițelor și sincronizarea nativă au trecut local.
- Starea CI pentru revizia publicată trebuie verificată în PR; rezultatele locale nu înlocuiesc GitHub Actions.

## Rămâne înainte de lansare publică

Validare pe dispozitive a stocării native securizate, configurare și verificare PostgreSQL/S3/SMTP, evaluare GDPR și retenție, documentația contractuală a furnizorilor AI și politica de confidențialitate, evaluare medicală a RAG/safety și OCR real. AI rămâne simulat; testele nu demonstrează interpretare medicală reală. Nicio infrastructură Render nu a fost modificată.

## Interpretarea intervalelor

Etichetele compară valoarea exclusiv cu intervalul din rezultat, fără diagnostic sau estimare automată a urgenței. Unitățile diferite necesită conversie validată; intervalele diferite nu sunt proiectate ca o singură bandă peste întregul grafic. Aceste precauții sunt conforme cu [explicația MedlinePlus despre rezultatele de laborator](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/). Nu există încă un catalog clinic validat de praguri critice.


### Chat: surse relevante și abținere

Chatul nu mai folosește rezumatele generate de AI ca dovezi și exclude valorile marcate `unverified`. Selectarea lexicală normalizează diacriticele și exclude fragmentele fără suprapunere cu întrebarea. Fără surse relevante, răspunsul de abținere este generat local, fără apel AI. Răspunsurile fără citări `[S1]` sau cu identificatori inexistenți sunt înlocuite cu abținere; lista surselor include numai citările folosite.

Limită: validarea identificatorilor nu demonstrează că fiecare afirmație este susținută de sursă și nu constituie validare medicală. Potrivirea lexicală poate rata sinonime sau întrebări de continuare. Corpusul de ghiduri clinice validate și routerul complet pentru urgențe rămân de implementat înaintea lansării publice.


### Interfața chatului

Sursele citate sunt afișate cu titlu și legătură către secțiunea dosarului. Erorile de trimitere sunt anunțate accesibil și păstrează întrebarea pentru reîncercare. Sunt verificate încă trei scenarii de browser (desktop/iPhone/Android), pe lângă cele nouă existente: surse, abținere și eroare de consimțământ. Buildul web și TypeScript au trecut. Chatul afișează permanent indicația 112 pentru urgențe.


### Router local de siguranță pentru chat (increment limitat)

Expresiile explicite despre dificultăți severe de respirație, durere toracică, inconștiență și anumite semne neurologice declanșează un mesaj local condițional pentru apelarea 112. Acest traseu nu apelează modelul și rămâne disponibil fără consimțământ pentru procesarea AI; celelalte întrebări păstrează verificarea consimțământului. Nu oferă diagnostic, doză sau prescripție.

Regulile lexicale nu reprezintă triaj clinic validat: pot omite formulări, alte urgențe sau pot reacționa la descrieri istorice/negate. Absența unei alerte nu înseamnă siguranță. Acoperirea altor instrumente AI și validarea clinică rămân deschise.

Surse consultate la 21 septembrie 2026: [serviciul public 112](https://serviciipublice.gov.ro/serviciu/serviciul-de-urgenta-112-asigurat-cetatenilor), [NHS – heart attack](https://www.nhs.uk/conditions/heart-attack/), [NHS – stroke symptoms](https://www.nhs.uk/conditions/stroke/symptoms/). Recomandarea telefonică este localizată pentru România; numărul britanic nu este afișat ca număr local.


### Export PDF/Word extins

Raportul include descrierile din istoric, toate măsurătorile de laborator cu data/intervalul/verificarea tehnică, alergii, vaccinări și programări, alături de tratamentele active. PDF-ul încorporează DejaVu Sans (licență inclusă), păstrează diacriticele, tratează caracterele speciale ca text și împarte celulele lungi pe pagini. Sunt verificate conținutul ambelor formate, separarea conturilor și un text de istoric care depășește o pagină. PDF-ul fictiv de control a fost randat și inspectat vizual pe ambele pagini. Raportul clinic nu înlocuiește exportul GDPR și nu încorporează fișierele originale.


### Recuperarea procesării documentelor

Migrarea `d0f2a4b6c8e0` adaugă un identificator și un termen de 20 de minute pentru fiecare încercare. O procesare abandonată poate fi reîncercată din interfață după expirare. Un proces vechi este respins înainte de modificarea rezultatelor dacă altă încercare a preluat documentul sau documentul a fost șters. Rezultatele precedente rămân păstrate la eșec. Testele acoperă expirarea, suprascrierea concurentă și ștergerea în timpul extragerii. Reîncercarea este manuală; nu este încă o coadă automată de extragere.


### PostgreSQL și audit backend

CI include PostgreSQL 16 temporar, migrarea completă, `alembic check` și testele backend în scheme separate. Verificarea a trecut la revizia `19db711`; definițiile enum și unicitatea abonamentului au fost aliniate cu migrările existente, fără modificarea datelor. Aplicația locală rămâne SQLite. Testul nou de consum concurent pe PostgreSQL este rulat numai în acel mediu și este omis explicit local.

Auditul `pip-audit 2.10.1`, la 21 septembrie 2026, a trecut de la 8 pachete afectate (164 înregistrări de vulnerabilitate raportate) la 0 după actualizare. Setul nou rezolvat are 87 pachete pe Windows. Versiunile corectate: FastAPI 0.141.1, Starlette 1.3.1, python-multipart 0.0.31, PyJWT 2.13.0, cryptography 50.0.0, pypdf 6.16.1, Pillow 12.3.0, pydicom 3.0.2, pytest 9.0.3 și pytest-asyncio 1.4.0. `pip check`, Ruff și 208 teste locale au trecut (testul PostgreSQL este omis pe SQLite). Auditul devine condiție CI; rezultatul reflectă baza de vulnerabilități disponibilă în momentul rulării, nu o garanție absolută de securitate.


### Loguri fără conținutul cererilor AI

Erorile aplicației pentru furnizorii AI și căutarea locațiilor înregistrează tipul excepției sau codul HTTP, nu corpul răspunsului, adresa căutată sau textul excepției. Diagnosticarea brută `pypdf` este oprită deoarece poate include bytes din fișierul invalid; procesarea păstrează un mesaj tehnic sanitizat. Testele folosesc marcatori fictivi sensibili și verifică absența lor din loguri. Configurarea logurilor serviciilor externe/proxy rămâne o verificare separată de deploy.

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

- Backend: 233 teste trecute și două teste PostgreSQL omise explicit local, inclusiv consum concurent, token expirat/reutilizat/scop greșit, autentificare, MFA, sesiuni și acces documente între utilizatori.
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


### Confirmarea tehnică a analizelor

Concordanța AI/parser verifică numele analitului, valoarea, unitatea și ambele limite de referință; nu acceptă diferențe numerice de 0,5% și nici etichete `verified` declarate de furnizor fără verificare. Normalizarea unităților modifică numai scrierea unor unități echivalente, fără conversii mg/dL ↔ mmol/L. Numerele cu separator ambiguu (de exemplu `1.234`) rămân fără valoare numerică, păstrând textul pentru verificare. Parserul cere delimitare între valoare, unitate și interval.

Valorile `unverified` nu sunt interpretate de AI, nu intră în grafice/comparații și sunt neevaluabile în dashboard. Migrarea `e1f3a5b7c9d0` corectează clasificările pentru rândurile deja marcate astfel și invalidează explicațiile vechi. Rândurile vechi marcate anterior `verified` necesită reprocesarea documentului pentru aplicarea regulilor noi; butonul este disponibil și pentru documentele procesate cu succes. Confirmarea tehnică nu înseamnă validare medicală.


### Rezultate de laborator editabile

API-ul și interfața permit creare, corectare și ștergere confirmată. Accesul este limitat la proprietar; operațiile sunt auditate fără valori medicale în jurnal. Corectarea înlocuiește toate câmpurile editabile, recalculează eticheta față de intervalul furnizat și invalidează explicațiile pentru seriile afectate. Originalul rămâne neschimbat; reprocesarea poate înlocui corectura, fapt indicat explicit în formular. Blocarea documentului serializează modificările față de procesare. Confirmarea manuală este transcriere, nu validare clinică.

Testele noi acoperă izolarea conturilor, auditul, invalidarea explicațiilor, date invalide, protecția în timpul procesării și păstrarea originalului. Fluxul browser creare → corectare → reîncărcare → anularea ștergerii → ștergere a trecut pe cele trei dimensiuni; suita browser are 15 scenarii trecute. Erorile explicațiilor și comparațiilor AI sunt afișate în pagină.


### Notificări cu rezultate de livrare explicite

Dezînregistrarea dispozitivelor este limitată la contul autentificat, cu validarea tokenului/platformei. API-ul test-push returnează separat delivered (acceptat de furnizor), simulated, failed și devices; Profil și Setări afișează mesaje distincte. Simularea nu marchează notificările sent, iar crearea unei înregistrări nu pretinde livrarea. Notificările viitoare sau de alt canal nu sunt trimise prin push. Eșecurile păstrează tokenurile pentru reîncercare.

Memento-urile push conțin un text generic și identificatorul notificării, fără titlu/body medical. Logurile nu includ titluri sau conținutul excepțiilor FCM. Testele acoperă izolarea conturilor, date invalide, păstrarea tokenurilor, simularea versus acceptarea reală, protecția conținutului și programările viitoare. Livrarea automată push este adăugată în incrementul următor descris mai jos; validarea pe telefon real rămâne deschisă; stările sent istorice nu dovedesc livrarea reală.

Verificare pentru acest increment: 227 teste backend locale trecute, un test PostgreSQL omis local, Ruff și build/TypeScript trecute; 18 scenarii browser trecute pe desktop și dimensiuni iPhone/Android. Testele de mesaje push din browser folosesc răspunsuri simulate; nu demonstrează livrarea FCM.


### Programări și proces automat de memento-uri

Crearea/reprogramarea/anularea/ștergerea actualizează memento-ul în aceeași tranzacție. Interfața permite reprogramare, schimbarea stării și ștergere confirmată, plus pregătirea memento-urilor lipsă pentru înregistrări vechi. Orele cu fus explicit se normalizează UTC și sunt reafișate local fără decalaj. Intervalele de timp invalide sunt respinse. Dashboardul nu numără memento-uri viitoare ca necitite.

Migrarea f2a4b6c8d0e1 adaugă rezervări și reîncercări persistente pentru livrări push. Procesul integrat revine după repornire, folosește o rezervare atomică și respinge confirmarea unui proces înlocuit. Simularea nu marchează livrarea, iar notificările viitoare, citite sau pentru programări expirate/anulate nu sunt expediate. Acceptarea de către furnizor nu dovedește afișarea pe telefon; întreruperea dintre acceptare și confirmarea DB poate genera duplicate. Canalele de notificare email/SMS și urmărirea livrării separat pe dispozitive rămân deschise.

Testele acoperă reîncercarea, rezervarea activă/expirată, un proces vechi înlocuit, transcrierea orei cu fus, actualizarea/anularea memento-ului și date invalide. Testul cu două conexiuni independente rulează numai pe PostgreSQL. Cele 21 de scenarii browser au trecut, inclusiv programare → reprogramare → reîncărcare → anulare → reactivare → ștergere pe cele trei dimensiuni.

Suită backend finală pentru memento-uri: 233 teste trecute, două teste PostgreSQL omise explicit local; Ruff trecut.

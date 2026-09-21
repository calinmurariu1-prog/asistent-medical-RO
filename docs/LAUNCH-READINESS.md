# Raport pentru versiunea locală — 21 septembrie 2026

Repository: calinmurariu1-prog/asistent-medical-RO. Livrare pe `codex/medical-launch-readiness`, PR #21. Vezi [instrucțiunile locale](LOCAL-TEST.md).

## Implementat

- Analizele fără interval/valoare numerică sunt neevaluabile; nu se deduc praguri critice generice. Graficele/comparațiile sunt blocate pentru unități incompatibile sau cronologie incertă; migrarea elimină clasificările și explicațiile vechi.
- Acord AI explicit în Setări, legat de furnizor; obligatoriu înaintea tuturor apelurilor către AI extern, cu retragere și verificare pe server.
- Ștergere cont/document cu curățarea persistentă și reîncercarea originalelor; status explicit pentru fișiere în curs, emailuri locale eliminate și relații SQLite active.
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

- Backend: 175 teste trecute, inclusiv consum concurent, token expirat/reutilizat/scop greșit, autentificare, MFA, sesiuni și acces documente între utilizatori.
- Ruff trecut; build Next și TypeScript trecute; zece teste unitare pentru refresh/concurență trecute.
- Export web Capacitor: 36 pagini construite. Nu au fost testate dispozitive fizice și nu s-au produs APK/IPA semnate.
- Verificările browser acoperă cont, confirmare, profil, PDF, descărcare identică, analize, dashboard, refresh, resetare și deconectare pe desktop și dimensiuni iPhone/Android. Capturi în `docs/screenshots`.
- Auditul npm complet (inclusiv dezvoltare): zero vulnerabilități raportate după actualizarea Capacitor 8.5.2 și a dependențelor indirecte. Generarea iconițelor și sincronizarea nativă au trecut local.
- Starea CI pentru revizia publicată trebuie verificată în PR; rezultatele locale nu înlocuiesc GitHub Actions.

## Rămâne înainte de lansare publică

Validare pe dispozitive a stocării native securizate, configurare și verificare PostgreSQL/S3/SMTP, evaluare GDPR și retenție, documentația contractuală a furnizorilor AI și politica de confidențialitate, evaluare medicală a RAG/safety și OCR real. AI rămâne simulat; testele nu demonstrează interpretare medicală reală. Nicio infrastructură Render nu a fost modificată.

## Interpretarea intervalelor

Etichetele compară valoarea exclusiv cu intervalul din rezultat, fără diagnostic sau estimare automată a urgenței. Unitățile diferite necesită conversie validată; intervalele diferite nu sunt proiectate ca o singură bandă peste întregul grafic. Aceste precauții sunt conforme cu [explicația MedlinePlus despre rezultatele de laborator](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/). Nu există încă un catalog clinic validat de praguri critice.

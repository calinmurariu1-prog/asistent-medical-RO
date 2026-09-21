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


## Notificări: simulare și confidențialitate

Testul push din Profil/Setări separă simularea locală, acceptarea de către furnizor și eșecul trimiterii. Acceptarea nu confirmă afișarea pe telefon. Fără FCM configurat, nu se trimit notificări reale. Mesajele push pentru memento-uri folosesc un text generic; detaliile medicale se consultă numai în aplicație. Tokenurile se dezînregistrează numai din contul proprietar, iar o eroare temporară nu le șterge.

Notificările nou create rămân pending până la o trimitere reală; simularea nu completează sent_at. Livrarea programată push este asigurată de procesul automat descris mai jos; canalele email/SMS pentru notificări rămân neimplementate. Stările sent din versiunile anterioare nu constituie dovadă de livrare reală și nu sunt rescrise automat. Tokenurile expirate necesită dezînregistrare explicită; eliminarea automată va necesita distingerea erorilor permanente de cele temporare.


## Memento-uri automate pentru programări

Programările noi creează memento-ul în aceeași tranzacție: cu 24 de ore înainte sau imediat pentru programări mai apropiate. Reprogramarea înlocuiește memento-ul, anularea/ștergerea îl elimină, iar reactivarea îl pregătește din nou. Pentru înregistrări din versiuni vechi folosește butonul „Pregătește memento-urile programărilor vechi”. Orele API necesită fus orar și sunt normalizate UTC; interfața introduce și afișează ora locală a dispozitivului.

Migrarea f2a4b6c8d0e1 adaugă rezervarea livrării și reîncercările. `NOTIFICATION_WORKER_ENABLED=true` activează procesul integrat; `NOTIFICATION_INTERVAL_SECONDS=30` stabilește intervalul (5–3600 secunde). Procesul scanează maximum 25 de înregistrări la fiecare trecere, rezervă fiecare încercare pentru 5 minute și reînnoiește rezervarea înaintea fiecărui dispozitiv. Erorile sunt reîncercate după 2–60 minute, cu starea păstrată în DB. Fără FCM real, procesul lasă notificările pending; nu execută trimiteri simulate repetate.

Numărul de necitite și „marchează toate citite” exclud notificările cu termen viitor. O notificare marcată explicit citită nu se mai trimite. Notificările pentru programări expirate/anulate sau utilizatori inactivi nu sunt expediate. SENT înseamnă acceptare pentru cel puțin un dispozitiv, nu afișare confirmată pe toate dispozitivele.

Limite: un mesaj deja acceptat de furnizor nu poate fi retras la anularea programării. Dacă procesul cade după acceptare dar înaintea confirmării în DB, o reluare poate produce duplicate; nu revendicăm livrare exact o dată. Reîncercările pe dispozitive individuale după acceptarea parțială nu sunt încă separate. Livrarea FCM reală, APNs și permisiunile dispozitivului necesită configurare externă și verificare fizică. Nu folosi aceste memento-uri pentru urgențe.


## Centrul de notificări

Pagina `/notifications` este accesibilă din antet, meniu și cardul din dashboard. Filtrele Necitite/Viitoare/Toate separă mesajele curente de memento-urile programate. „Marchează toate notificările curente citite” păstrează memento-urile viitoare. Ștergerea cere confirmare și oprește încercările viitoare, fără să retragă mesaje deja trimise. Linkul unei programări deschide și aduce în ecran cardul asociat.

Lista se actualizează la 30 de secunde cât pagina este vizibilă și la revenirea în fereastră; butonul Actualizează permite reîncărcarea imediată. Citirea în aplicație nu confirmă afișarea unei notificări push pe telefon.


## Medicație și istoric

Medicamente permite înregistrarea și corectarea denumirii, substanței active, dozei/frecvenței transcrise, instrucțiunilor, perioadei și notelor. Listele Active/Istoric sunt controlate explicit de utilizator; mutarea în istoric păstrează datele și nu reprezintă o recomandare de oprire a tratamentului. Ștergerea definitivă cere confirmare.

Perioada este validată în formular și pe server, inclusiv la modificarea unui singur capăt al intervalului. Accesul este separat pe cont, iar jurnalul reține tipul operației și ID-ul, fără doze sau note. Datele vechi care depășesc limitele noilor formulare rămân citibile. Actualizarea listei elimină verificările și explicațiile afișate anterior pentru a evita rezultate învechite.

Verificarea interacțiunilor folosește încă o listă locală limitată; lipsa potrivirilor nu confirmă siguranța combinației. Catalogul educațional cu surse este descris mai jos; validarea clinică, extinderea acoperirii și memento-urile de medicație la ore alese explicit rămân de finalizat. Nu se deduce un orar de administrare din textul liber al frecvenței.


## Sursele verificării limitate a medicației

Catalogul educațional consultat la 21 septembrie 2026 cuprinde cinci perechi: warfarină/aspirină și warfarină/ibuprofen ([NHS warfarin](https://www.nhs.uk/medicines/warfarin/)), aspirină/ibuprofen ([NHS aspirin](https://www.nhs.uk/medicines/aspirin/)), simvastatină/claritromicină ([NHS SPS](https://sps.nhs.uk/articles/managing-interactions-between-macrolides-and-statins/)), levotiroxină/omeprazol ([NHS levothyroxine](https://www.nhs.uk/medicines/levothyroxine/)). Fiecare alertă include sursa și data consultării; această dată nu înseamnă validare de către un clinician.

Se potrivesc numai substanțele declarate explicit și câteva sinonime română/engleză, fără deducție din marcă sau interpretarea preparatelor combinate. API raportează numărul perechilor fără regulă și medicamentele cu substanță absentă/nerecunoscută. Perechile de substanțe identice pot avea un mesaj separat de repetare, dar nu primesc o evaluare clinică. Severity este acum `requires_review`, nu un scor medical. Nu se evaluează doze, funcție renală, boli asociate sau siguranță individuală.

Regulile vechi enalapril/spironolactonă, sertralină/tramadol și metformin/furosemid sunt retrase din catalog până la documentare și evaluare clinică; apar ca neevaluate, niciodată drept combinații sigure. Catalogul nu este exhaustiv și necesită revizie clinică înaintea utilizării reale. Nu există căutări externe cu datele pacientului. Memento-urile de medicație la ore alese explicit rămân de implementat.


## Explicația educațională a unui medicament

`/ai/skills/explain_medication` folosește un catalog inițial de trei substanțe (warfarină, aspirină, levotiroxină), cu rezumate românești din paginile NHS citate și consultate la 21 septembrie 2026. Butonul Explică folosește substanța activă declarată; denumirile comerciale și combinațiile necunoscute primesc un răspuns de informație insuficientă, fără apel la furnizorul AI. Extinderea catalogului și revizia clinică rămân necesare.

În modul simulat se afișează explicit un rezumat local cu sursa, nu o interpretare AI. Furnizorul real primește numai fragmentul catalogului și denumirea canonică, fără numele comercial sau datele dosarului. Răspunsurile fără citarea M1 sau cu alte identificatoare de citare sunt înlocuite cu abstinență. Răspunsul API include sources, simulated și abstained, iar pagina Medicație oferă linkul sursei. Verificarea identificatorului nu demonstrează că fiecare afirmație este susținută de sursă; evaluarea clinică a furnizorului real rămâne obligatorie. Nu se oferă doze sau modificări autonome de tratament. Celelalte funcții AI sunt în curs de audit separat.


## Semnale de urgență în capabilitățile AI

Toate formularele `/ai/skills/{name}` verifică local câmpurile declarate de capabilitate înaintea inițializării furnizorului AI și a verificării consimțământului AI. Semnalele recunoscute primesc mesajul condițional 112, sursele publice și `emergency=true`, fără generare externă sau verificare de disponibilitate MedLLM. Autentificarea rămâne necesară. Cererile obișnuite păstrează consimțământul obligatoriu pentru furnizorul extern. Câmpurile suplimentare nu pot schimba acest comportament.

Pagina Asistent afișează mesajul cu rol de alertă și linkurile surselor. Regulile lexicale sunt limitate, pot produce alerte și pentru texte citate/istorice și nu detectează toate urgențele. Lipsa alertei nu exclude o urgență. Nu reprezintă triaj clinic validat; celelalte răspunsuri medicale ale capabilităților sunt în curs de audit al surselor.


## Celelalte capabilități educaționale

Nu mai există un fallback care solicită modelului recomandări medicale fără surse pentru cele șase capabilități. Catalogul inițial pentru simptome acoperă exact durere de cap/cefalee și oboseală, cu sursele [NHS Headaches](https://www.nhs.uk/symptoms/headaches/) și [NHS Tiredness and fatigue](https://www.nhs.uk/symptoms/tiredness-and-fatigue/). Stilul de viață acoperă diabetul de tip 2, din [NHS Treatment](https://www.nhs.uk/conditions/type-2-diabetes/treatment/). Fragmentele românești au fost consultate la 21 septembrie 2026; catalogul nu are validare clinică și are acoperire restrânsă. Pagina NHS despre oboseală indică o dată de revizuire planificată deja trecută; actualitatea clinică trebuie reverificată înaintea lansării. Nu se folosesc potriviri aproximative pentru simptome complexe.

Subiectele necunoscute primesc abstinență fără apel de generare. Modurile simulate sunt etichetate și arată fragmentele locale cu citări. Generarea reală folosește numai fragmentul selectat și respinge citările absente sau cu identificatoare necunoscute; această verificare nu dovedește susținerea fiecărei afirmații de către sursă.

Simplificarea reală citează textul utilizatorului ca sursă neverificată clinic, fără a-i atribui autoritate medicală. În modul simulat nu pretinde reformulare: redă integral originalul, inclusiv finalul și negațiile. Cererile au maximum 8 câmpuri de maximum 12.000 caractere fiecare. Pregătirea vizitei produce local întrebări pentru medic, nu recomandări clinice. Verificarea rețetei compară numai substanțe separate explicit prin punct și virgulă/rând nou (maximum 30) cu catalogul limitat de interacțiuni; mărcile, dozele și combinațiile nerecunoscute rămân neevaluate. Nu verifică validitatea unei prescripții.

Auditul nu este încheiat pentru rezumatul dosarului, comparațiile analizelor și explicațiile de laborator, care au fluxuri separate. Integrarea surselor clinice extinse și evaluarea furnizorului real rămân cerințe pentru lansare.


## Rezumatul dosarului și comparația analizelor

Rezumatul citează înregistrări proprii din analize, istoric (inclusiv diagnostice/observații), medicație activă și istorică, alergii, vaccinuri, programări și inventarul documentelor. Include cel mult 20 de înregistrări din fiecare secțiune, ordonate după adăugare, și semnalează explicit când este parțial. Prezintă câmpuri factuale selectate; nu analizează conținutul originalelor sau toate notele și nu reprezintă exportul complet. Identificatorii și tipurile surselor sunt întorși în API și în legenda vizibilă; sursele sunt date înregistrate, nu dovezi clinice independente. Nu sunt trimise numele pacientului, CNP-ul sau datele de contact.

Valorile neconfirmate nu sunt incluse numeric nici în rezumat, nici în comparația cu o singură valoare. Comparația cere date distincte și unități compatibile, citează prima și ultimele două măsurători și calculează diferența ultimelor două. Nu echivalează creșterea/scăderea cu agravarea/ameliorarea. Datele lipsă sau incompatibile produc abstinență. Dosarul gol nu produce apel de generare.

Modul simulat este etichetat; modelul real primește faptele cu referințe și răspunsurile fără citări valide sunt înlocuite cu abstinență. Validarea identificatorilor nu garantează susținerea fiecărei afirmații sau corectitudinea clinică. Explicațiile individuale de laborator au încă un flux separat, care rămâne de auditat.


## Explicații individuale ale analizelor

Explicațiile individuale folosesc acum valoarea, unitatea și intervalul din înregistrare, cu referința L + ID-ul rezultatului. Descriu poziția numerică față de interval; nu adaugă cauze sau diagnostice din vechiul catalog fără surse. Lipsa confirmării, a valorii numerice, a unității sau a celor două limite valide produce un mesaj de informație insuficientă, fără generare externă. Pentru semnificația clinică individuală rămân necesare surse și evaluare clinică separate.

Generarea reală trece prin aceeași verificare a citărilor ca rezumatul dosarului. Modului simulat îi corespunde un rezumat factual local etichetat explicit. Nu se mai adaugă automat tendința întregului istoric la explicația unei valori izolate; comparația are endpoint separat.

Salvarea compară atomic câmpurile sursei cu copia folosită la generare. Dacă analiza a fost corectată sau ștearsă între timp, textul vechi nu se salvează și cererea individuală răspunde 409; lotul ignoră înregistrarea schimbată și returnează lista actuală. Tranzacția de citire nu rămâne deschisă pe durata generării externe. Migrarea a3c5e7f9b1d2 golește doar cache-ul vechi de explicații, păstrând rezultatele și documentele originale. Explicațiile se regenerează la cerere; downgrade-ul nu reconstituie textele vechi.


## Memento-uri zilnice pentru medicație

În cardul unui tratament, Memento-uri permite alegerea explicită a orei și fusului orar IANA, modificarea, pauza/reactivarea și ștergerea cu confirmare. Sunt permise cel mult 12 ore zilnice pe tratament. Nu se deduce ora din doza sau frecvența în text liber. Fusul rămâne cel ales când utilizatorul călătorește; următoarea apariție este afișată și în ora dispozitivului.

Migrarea b4d6f8a0c2e3 păstrează programul și următoarea apariție în baza de date. Notificarea viitoare este creată în aceeași tranzacție cu programul. Workerul existent avansează cursorul și creează următoarea notificare o singură dată, sub blocarea tratamentului. Funcționează și în modul push simulat, prin centrul de notificări. Livrarea reală continuă să necesite configurarea FCM/APNs și permisiunile dispozitivului.

La schimbarea orei de vară, o oră locală inexistentă este omisă pentru acea zi, iar ora repetată folosește prima apariție, fără dublare. Intervalul tratamentului și starea activ/istoric sunt respectate; modificarea tratamentului recalculează memento-urile. Pauza, schimbarea orei sau ștergerea elimină notificările asociate și orice rezervare de trimitere; mesajele deja acceptate de furnizor nu pot fi retrase. Exportul datelor include programele, iar ștergerea contului/tratamentului le elimină prin relații cu ștergere în cascadă.

Workerul nu creează retrospectiv notificări pentru zilele ratate și nu trimite push pentru un memento de medicație întârziat cu peste 15 minute. Notificarea poate rămâne vizibilă în aplicație. Nu confirmă administrarea și nu recomandă recuperarea dozelor omise. Scanarea procesează până la 100 programe la fiecare ciclu; disponibilitatea procesului și întârzierile furnizorului pot afecta punctualitatea. Nu sunt alarme clinice garantate și nu au fost verificate pe dispozitive fizice. Recurențele săptămânale și confirmarea administrării rămân de implementat.


### Încărcări întrerupte și originale fără document
Înainte de salvarea originalului se confirmă în baza de date o intenție de curățare cu cheia criptată. Salvarea documentului și anularea acestei intenții sunt atomice; un blocaj pe aceeași înregistrare împiedică workerul să șteargă un original în curs de confirmare. Dacă procesul se oprește sau salvarea eșuează, workerul reia curățarea după expirarea rezervării de 10 minute. Workerul trebuie să fie activ și baza de date/stocarea disponibile. Un răspuns de eroare cu rezultat incert cere reîncărcarea listei înainte de repetare.
Fișierele temporare locale noi au un nume determinist derivat din cheia unică, astfel încât curățarea elimină și scrierile locale întrerupte. Resturile temporare din versiuni anterioare nu sunt migrate automat. Nu există atomicitate distribuită cu S3: confirmările foarte întârziate de la furnizor, versiunile istorice, Object Lock și backupurile necesită reconciliere/politici externe. Testele simulează eroare după scriere, eșec de commit și confirmare de commit pierdută; nu revendică testare pe un serviciu S3 real.


### Export JSON al dosarului — schema 2
Exportul autentificat păstrează cheile existente și adaugă identificatori, datele creării/modificării, contacte de urgență, furnizorul vaccinului, legături ale istoricului, rezultate textuale și nivelul de verificare al analizelor, textul extras și metadatele documentului, perioade/note/instrucțiuni ale medicației și detalii ale programărilor. Orele sunt exportate cu fus orar; datele calendaristice rămân date. Metadatele JSON vechi nevalide sunt păstrate ca `unparsed_text`, fără să blocheze restul exportului.
`export_metadata` declară explicit acoperirea. Originalele nu sunt încorporate în JSON; fiecare document oferă o cale de descărcare care necesită autentificarea proprietarului. CNP, datele dispozitivelor de sănătate, notificările, feedbackul, facturarea și auditul nu sunt încă incluse. Secretele de autentificare și cheile interne de stocare nu se exportă. Răspunsul are `Cache-Control: no-store`; fișierul descărcat rămâne în responsabilitatea utilizatorului. Acest increment nu reprezintă un pachet integral de portabilitate și nu certifică conformitatea juridică GDPR.

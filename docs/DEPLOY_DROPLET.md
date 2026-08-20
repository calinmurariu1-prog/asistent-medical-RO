# Deploy pe un Droplet DigitalOcean (Docker Compose)

Tot stack-ul pe **un singur server**: PostgreSQL + MinIO (documente) + backend +
frontend + Caddy (HTTPS automat). Cel mai ieftin: un Droplet de **~6 $/lună**
(1 GB RAM) ține totul pentru început; recomandat **2 GB** (~12 $/lună) ca să ai
loc de build + OCR.

## De ce ai nevoie înainte
1. **Un domeniu** (ex. `exemplu.ro`). Fără domeniu nu ai HTTPS, iar unele funcții
   din browser (locația la „Găsește medici") cer HTTPS.
2. Cheia **Groq** gratuită: <https://console.groq.com/keys>.

---

## Pasul 1 — Creează Droplet-ul
1. DigitalOcean → **Create → Droplets**.
2. **Marketplace → Docker** (imagine cu Docker preinstalat). Regiune **Frankfurt**.
3. Plan: **Basic**, minim **2 GB / 1 CPU**. Autentificare: **SSH key** (recomandat).
4. Create. Notează **IP-ul** droplet-ului.

## Pasul 2 — DNS (2 înregistrări A)
La registrarul domeniului, adaugă:
| Tip | Nume | Valoare |
|-----|------|---------|
| A | `app` (→ `app.exemplu.ro`) | IP-ul droplet-ului |
| A | `files` (→ `files.exemplu.ro`) | IP-ul droplet-ului |

(Poți folosi și domeniul principal `@` în loc de `app`, dar cu subdomenii e mai clar.)

## Pasul 3 — Intră pe server și ia codul
```bash
ssh root@IP_DROPLET

# clonează repo-ul (branch-ul de lucru)
git clone -b claude/new-isolated-project-oheqvr \
  https://github.com/calinmurariu1-prog/asistent-medical-RO.git
cd asistent-medical-RO
```

## Pasul 4 — Configurează secretele
```bash
cp .env.prod.example .env
nano .env        # completează valorile (vezi mai jos)
```
Generează secrete tari direct pe server:
```bash
# SECRET_KEY
openssl rand -base64 48
# DATA_ENCRYPTION_KEY
openssl rand -base64 32
# parole DB / MinIO
openssl rand -base64 24
```
Completează în `.env`: `APP_DOMAIN`, `FILES_DOMAIN`, `SECRET_KEY`,
`DATA_ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`,
`GROQ_API_KEY`, plus `BACKEND_CORS_ORIGINS` și `FRONTEND_URL` = `https://APP_DOMAIN`.

## Pasul 5 — Pornește
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
Prima construire durează câteva minute (build backend + frontend). Caddy obține
automat certificatele HTTPS după ce DNS-ul e propagat.

Verifică:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend   # migrațiile rulează la boot
```

Deschide **https://APP_DOMAIN** 🎉

---

## Operare
```bash
# loguri
docker compose -f docker-compose.prod.yml logs -f

# actualizare după un push nou
git pull
docker compose -f docker-compose.prod.yml up -d --build

# oprire
docker compose -f docker-compose.prod.yml down          # păstrează datele (volume)
```

## Firewall (recomandat)
```bash
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```
Porturile DB/MinIO **nu** sunt publicate — sunt accesibile doar în rețeaua internă
Docker (MinIO iese la internet doar prin Caddy, pe `FILES_DOMAIN`).

## Note
- **AI:** implicit Groq. Fără `GROQ_API_KEY` → mock offline (app-ul pornește oricum).
- **Backup DB:**
  `docker compose -f docker-compose.prod.yml exec db pg_dump -U medai asistent_medical > backup.sql`
- **Google Maps în app:** `GOOGLE_MAPS_API_KEY` în `.env`; pentru harta din browser,
  cheia e build-time — adaugă `NEXT_PUBLIC_GOOGLE_MAPS_KEY` ca build arg în
  `docker-compose.prod.yml` (serviciul `frontend`, `args`). Vezi `docs/AI_AND_MAPS.md`.
- **Memorie mică (1 GB):** build-ul frontend poate rămâne fără RAM. Fie iei 2 GB,
  fie adaugi swap: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`.

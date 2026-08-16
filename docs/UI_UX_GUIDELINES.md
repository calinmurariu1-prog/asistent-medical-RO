# Ghid UI/UX (aplicat în app)

Principii de design pe care le urmăm în aplicație. Adaptat după skill-ul
open-source **[ceorkm/mobile-app-ui-design](https://github.com/ceorkm/mobile-app-ui-design)**
(licență MIT) — metodologie + reguli, aplicate la contextul „health".

## Proces (5 pași)
1. **Context** — tip app, utilizator, acțiune principală, convenții de industrie (health).
2. **Structură (UX)** — acțiunile principale în *thumb zone* (bara de jos), conținut expus direct, stări goale transformate în ghidare.
3. **Vizual (UI)** — vezi regulile de mai jos.
4. **Emoție (Peak-End)** — momentele-cheie cu micro-animații (inele care se umplu, feedback la succes), finaluri cu carduri de sumar.
5. **Polish** — glow subtil, umbre soft tentate, target-uri ≥ 44px, stări error/empty/loading/success.

## Reguli vizuale
- **Tipografie:** o singură familie; max 4 mărimi / 2 greutăți; ierarhie prin
  mărime + greutate + opacitate; **numere mari cu `tabular-nums`** (statistici, prețuri).
- **Culoare 60/30/10:** 60% neutru (fundal), 30% text/elemente închise, 10% brand
  (CTA, iconițe, indicatori). Opacități text: 100% titluri, 80% body, 60–70% secundar.
- **Grid 8pt:** spații divizibile cu 4/8 (8, 12, 16, 24, 32, 48…). Elemente
  legate → mai aproape; grupuri diferite → mai depărtate.
- **Umbre:** mereu **soft**, tentate spre culoarea elementului (nu gri/negru pur).
- **Iconițe/imagini:** avatar/foto > inițiale > iconițe generice; categorii cu
  fundal soft colorat.

## Cum e reflectat în cod
- **Peak-End:** inelele de sănătate se animează la umplere (`HealthRing` +
  `framer-motion`); `Reveal` face fade/slide subtil pe carduri-cheie.
- **Numere:** `tabular-nums` pe dashboard, inele, prețuri, statistici.
- **Butoane:** ≥ 44px (tap target), umbre **tentate pe brand** (nu negru).
- **Umbre soft & carduri rotunjite:** token `--shadow-soft`, `rounded-3xl`.
- **Thumb zone:** bară de tab-uri jos pe mobil.
- **Stări goale:** componenta `EmptyState` (ghidare, nu text sec).

## Anti-pattern-uri de evitat
- >4 mărimi de font sau >3 greutăți; spații ne-aliniate la grid.
- CTA în afara *thumb zone*; conținut ascuns după tap-uri inutile.
- Umbre gri/negre pe fundaluri colorate; gradient/blur în exces (fără scop).
- Etichete mai proeminente decât valorile.

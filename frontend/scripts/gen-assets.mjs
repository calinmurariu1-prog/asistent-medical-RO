// Rasterize the brand logo into the source assets @capacitor/assets needs.
// Produces frontend/assets/{icon-only,icon-foreground,icon-background,splash,splash-dark}.png
import sharp from "sharp";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const outDir = join(dirname(fileURLToPath(import.meta.url)), "..", "assets");
mkdirSync(outDir, { recursive: true });

// Mark geometry (48-unit viewBox), visual bbox ~ x[5,39.3] y[12,33].
const PULSE = "M5 29 H15 L19 18 L24 33 L27 24 H31";
const SPARK = "M37 12 l1.7 4.6 4.6 1.7 -4.6 1.7 -1.7 4.6 -1.7 -4.6 -4.6 -1.7 4.6 -1.7 z";
const BBOX = { cx: 22.15, cy: 21.2, w: 34.3 };

function markGroup(canvas, markWidth, mono) {
  const s = markWidth / BBOX.w;
  const tx = canvas / 2 - BBOX.cx * s;
  const ty = canvas / 2 - BBOX.cy * s;
  const stroke = mono ? "#ffffff" : "url(#gp)";
  const sparkFill = mono ? "#ffffff" : "url(#gs)";
  const dotFill = mono ? "#ffffff" : "#10B981";
  return `
    <g transform="translate(${tx} ${ty}) scale(${s})">
      <path d="${PULSE}" fill="none" stroke="${stroke}" stroke-width="3.4"
            stroke-linecap="round" stroke-linejoin="round"/>
      <path d="${SPARK}" fill="${sparkFill}"/>
      <circle cx="31" cy="24" r="2.4" fill="${dotFill}"/>
    </g>`;
}

const GRADS = `
  <defs>
    <linearGradient id="tile" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#2563EB"/><stop offset="1" stop-color="#7C3AED"/>
    </linearGradient>
    <linearGradient id="gp" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#2563EB"/><stop offset="0.55" stop-color="#7C3AED"/>
      <stop offset="1" stop-color="#10B981"/>
    </linearGradient>
    <linearGradient id="gs" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#2563EB"/><stop offset="1" stop-color="#7C3AED"/>
    </linearGradient>
  </defs>`;

function svg(size, inner) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${GRADS}${inner}</svg>`;
}

async function png(name, markup) {
  await sharp(Buffer.from(markup)).png().toFile(join(outDir, name));
  console.log("wrote", name);
}

await Promise.all([
  // Full-bleed gradient tile with the white mark (legacy / round icon).
  png("icon-only.png", svg(1024, `<rect width="1024" height="1024" fill="url(#tile)"/>${markGroup(1024, 560, true)}`)),
  // Adaptive icon: gradient background + white foreground mark (in safe zone).
  png("icon-background.png", svg(1024, `<rect width="1024" height="1024" fill="url(#tile)"/>`)),
  png("icon-foreground.png", svg(1024, markGroup(1024, 440, true))),
  // Splash: brand mark centered on light / dark background.
  png("splash.png", svg(2732, `<rect width="2732" height="2732" fill="#F4F7F6"/>${markGroup(2732, 760, false)}`)),
  png("splash-dark.png", svg(2732, `<rect width="2732" height="2732" fill="#060B19"/>${markGroup(2732, 760, false)}`)),
]);
console.log("done");

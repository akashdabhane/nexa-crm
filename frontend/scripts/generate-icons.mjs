// Generates every NexaCRM icon from the single logo mark defined below.
// Run after changing the mark: `node scripts/generate-icons.mjs` (uses `sharp`, which ships with Next.js).
import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const root = fileURLToPath(new URL("..", import.meta.url));
const out = (path) => `${root}${path}`;

// 64×64 mark: indigo tile, a white "N" whose right stem rises like a growth bar into a cyan node.
const mark = (radius) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#7c6cff"/>
      <stop offset=".55" stop-color="#4f39f6"/>
      <stop offset="1" stop-color="#3a24c9"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="${radius}" fill="url(#bg)"/>
  <path d="M20 45V19l24 26V31" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="44" cy="19" r="5" fill="#67e8f9"/>
</svg>
`;

const rounded = mark(14);
// Full-bleed square: iOS and Android apply their own mask to home-screen icons.
const square = mark(0);

const png = (svg, size) => sharp(Buffer.from(svg), { density: 72 * (size / 64) * 2 }).resize(size, size).png().toBuffer();

/** Packs PNG images into an .ico container (PNG-in-ICO, supported by every current browser). */
function ico(images) {
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(images.length, 4);
  let offset = 6 + 16 * images.length;
  const entries = images.map(({ size, data }) => {
    const entry = Buffer.alloc(16);
    entry.writeUInt8(size >= 256 ? 0 : size, 0);
    entry.writeUInt8(size >= 256 ? 0 : size, 1);
    entry.writeUInt16LE(1, 4); // colour planes
    entry.writeUInt16LE(32, 6); // bits per pixel
    entry.writeUInt32LE(data.length, 8);
    entry.writeUInt32LE(offset, 12);
    offset += data.length;
    return entry;
  });
  return Buffer.concat([header, ...entries, ...images.map(({ data }) => data)]);
}

const icoSizes = [16, 32, 48];
const icoImages = await Promise.all(icoSizes.map(async (size) => ({ size, data: await png(rounded, size) })));

await Promise.all([
  writeFile(out("src/app/icon.svg"), rounded),
  writeFile(out("src/app/favicon.ico"), ico(icoImages)),
  png(square, 180).then((data) => writeFile(out("src/app/apple-icon.png"), data)),
  png(rounded, 192).then((data) => writeFile(out("public/icon-192.png"), data)),
  png(rounded, 512).then((data) => writeFile(out("public/icon-512.png"), data)),
  png(square, 512).then((data) => writeFile(out("public/icon-maskable-512.png"), data)),
]);

console.log("Icons written: src/app/{icon.svg,favicon.ico,apple-icon.png}, public/icon-{192,512,maskable-512}.png");

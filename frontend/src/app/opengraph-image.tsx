import { ImageResponse } from "next/og";

import { site } from "@/lib/site";

// Social preview card (Open Graph; X/Twitter falls back to it). Rendered once at build time.
export const alt = site.title;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const FEATURES = ["Contacts", "Leads & deals", "Kanban pipeline", "Reports", "AI assistant"];

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          color: "#fff",
          background: "linear-gradient(135deg, #7c6cff 0%, #4f39f6 50%, #2a1aa3 100%)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <svg width="80" height="80" viewBox="0 0 64 64">
            <rect width="64" height="64" rx="14" fill="#ffffff" fillOpacity="0.16" />
            <path d="M20 45V19l24 26V31" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="44" cy="19" r="5" fill="#67e8f9" />
          </svg>
          <div style={{ fontSize: 44, fontWeight: 700, letterSpacing: -1 }}>{site.name}</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 72, fontWeight: 700, lineHeight: 1.05, letterSpacing: -2, maxWidth: 960 }}>
            {site.tagline}
          </div>
          <div style={{ fontSize: 30, opacity: 0.85, maxWidth: 900 }}>
            Every contact, lead and deal in one place, with an assistant that logs your sales work for you.
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          {FEATURES.map((feature) => (
            <div
              key={feature}
              style={{
                display: "flex",
                fontSize: 24,
                padding: "10px 22px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.14)",
                border: "1px solid rgba(255,255,255,0.25)",
              }}
            >
              {feature}
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}

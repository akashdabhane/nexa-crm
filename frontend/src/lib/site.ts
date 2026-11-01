/** Public-facing product info shared by metadata, the landing page, robots, sitemap and the web manifest. */
export const site = {
  name: "NexaCRM",
  // Absolute origin used for canonical URLs, Open Graph images and the sitemap. Set it in production.
  url: (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, ""),
  title: "NexaCRM – AI-Powered CRM for Small Sales Teams",
  tagline: "The AI-powered CRM for small sales teams",
  description:
    "NexaCRM is a modern CRM for small sales teams. Manage contacts, leads and deals on a drag-and-drop pipeline, track tasks and reports, and log sales work with an AI assistant.",
  keywords: [
    "CRM",
    "AI CRM",
    "sales CRM",
    "CRM for small business",
    "sales pipeline management",
    "lead management",
    "contact management",
    "deal tracking",
    "Kanban sales pipeline",
    "sales reports",
    "AI sales assistant",
  ],
  author: "Akash Dabhane",
  brandColor: "#4f39f6",
} as const;

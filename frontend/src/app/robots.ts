import type { MetadataRoute } from "next";

import { site } from "@/lib/site";

// The CRM itself sits behind login, so crawlers only need the public pages.
const PRIVATE_PATHS = [
  "/dashboard",
  "/reports",
  "/contacts",
  "/companies",
  "/leads",
  "/deals",
  "/pipeline",
  "/activities",
  "/tasks",
  "/notifications",
  "/settings",
  "/auth/",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: PRIVATE_PATHS }],
    sitemap: `${site.url}/sitemap.xml`,
  };
}

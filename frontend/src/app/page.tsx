import type { Metadata } from "next";

import { LandingView } from "@/features/landing/landing-view";
import { site } from "@/lib/site";

// Public landing page. Signed-in users never see it: proxy.ts redirects "/" to /dashboard for them.
export const metadata: Metadata = {
  title: { absolute: site.title },
  alternates: { canonical: "/" },
};

// Structured data so search engines understand what the product is (schema.org).
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${site.url}/#website`,
      url: `${site.url}/`,
      name: site.name,
      description: site.description,
      inLanguage: "en",
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${site.url}/#app`,
      name: site.name,
      url: `${site.url}/`,
      description: site.description,
      applicationCategory: "BusinessApplication",
      applicationSubCategory: "Customer Relationship Management",
      operatingSystem: "Web browser",
      image: `${site.url}/opengraph-image`,
      featureList: [
        "Contact and company management",
        "Lead management, scoring and one-click conversion",
        "Drag-and-drop Kanban sales pipeline",
        "AI sales assistant",
        "Tasks, activities and notifications",
        "Sales reports and dashboards",
        "Role-based permissions and audit log",
      ],
      author: { "@type": "Person", name: site.author },
    },
  ],
};

export default function Home() {
  return (
    <>
      <script
        type="application/ld+json"
        // JSON.stringify output is safe here; "<" is escaped so the payload can't close the script tag.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <LandingView />
    </>
  );
}

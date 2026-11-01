import type { Metadata } from "next";

import { ContactDetail } from "@/features/contacts/contact-detail";

export const metadata: Metadata = { title: "Contact" };

export default async function ContactPage({ params }: PageProps<"/contacts/[id]">) {
  const { id } = await params;
  return <ContactDetail id={id} />;
}

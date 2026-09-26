import { ContactDetail } from "@/features/contacts/contact-detail";

export default async function ContactPage({ params }: PageProps<"/contacts/[id]">) {
  const { id } = await params;
  return <ContactDetail id={id} />;
}

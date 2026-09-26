"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCurrentUser } from "@/hooks/use-current-user";

import { AuditLogSettings } from "./audit-log-settings";
import { PipelineSettings } from "./pipeline-settings";
import { ProfileSettings } from "./profile-settings";
import { UsersSettings } from "./users-settings";

export function SettingsView() {
  const { isAdmin, isManager } = useCurrentUser();
  const tabs = [
    { value: "profile", label: "Profile", content: <ProfileSettings />, show: true },
    { value: "users", label: "Users & roles", content: <UsersSettings />, show: isAdmin },
    { value: "pipeline", label: "Pipeline", content: <PipelineSettings />, show: isAdmin },
    { value: "audit", label: "Audit log", content: <AuditLogSettings />, show: isManager },
  ].filter((tab) => tab.show);

  return (
    <>
      <PageHeader title="Settings" description="Your profile and workspace configuration." />
      <Tabs defaultValue="profile">
        <TabsList>
          {tabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {tabs.map((tab) => (
          <TabsContent key={tab.value} value={tab.value} className="pt-2">
            {tab.content}
          </TabsContent>
        ))}
      </Tabs>
    </>
  );
}

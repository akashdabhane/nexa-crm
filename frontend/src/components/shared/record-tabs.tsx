"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type RecordTab = { value: string; label: string; content: React.ReactNode };

/** Card with tabs for a record's related data (timeline, deals, tasks, notes…). */
export function RecordTabs({ tabs }: { tabs: RecordTab[] }) {
  return (
    <Card>
      <CardContent>
        <Tabs defaultValue={tabs[0].value}>
          <TabsList className="w-full justify-start overflow-x-auto sm:w-fit">
            {tabs.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
          {tabs.map((tab) => (
            <TabsContent key={tab.value} value={tab.value} className="pt-4">
              {tab.content}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}

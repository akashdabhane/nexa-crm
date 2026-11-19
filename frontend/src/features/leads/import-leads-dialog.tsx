"use client";

import { FileUp } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/shared/form-field";
import { PLATFORM_LABELS, PlatformIcon } from "@/components/shared/platform-badge";
import { UserSelect } from "@/components/shared/user-select";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { importSummary } from "@/features/integrations/hooks";
import { useCurrentUser } from "@/hooks/use-current-user";
import { SOCIAL_PLATFORMS, type ImportResult, type SocialPlatform } from "@/types";

import { useImportLeads } from "./hooks";

const NOT_SOCIAL = "none";
const MAX_FILE_BYTES = 5 * 1024 * 1024;

/** Meta's lead exports are UTF-16 tab-separated; most others are UTF-8 CSV. */
async function readText(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (bytes[0] === 0xff && bytes[1] === 0xfe) return new TextDecoder("utf-16le").decode(bytes);
  if (bytes[0] === 0xfe && bytes[1] === 0xff) return new TextDecoder("utf-16be").decode(bytes);
  return new TextDecoder("utf-8").decode(bytes);
}

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

export function ImportLeadsDialog({ open, onOpenChange }: Props) {
  const { user, isManager } = useCurrentUser();
  const importLeads = useImportLeads();
  const fileInput = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [csvText, setCsvText] = useState<string | null>(null);
  const [platform, setPlatform] = useState<SocialPlatform | typeof NOT_SOCIAL>("facebook");
  const [score, setScore] = useState("0");
  const [ownerId, setOwnerId] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportResult | null>(null);

  const scoreNumber = Number(score);
  const scoreValid = /^\d+$/.test(score) && scoreNumber <= 100;

  function reset() {
    setFileName(null);
    setCsvText(null);
    setPreview(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function payload(text: string, dryRun: boolean) {
    return {
      csv_text: text,
      platform: platform === NOT_SOCIAL ? null : platform,
      score: scoreValid ? scoreNumber : 0,
      owner_id: isManager ? (ownerId ?? user?.id ?? null) : null,
      dry_run: dryRun,
    };
  }

  async function runPreview(text: string) {
    try {
      setPreview(await importLeads.mutateAsync(payload(text, true)));
    } catch {
      setPreview(null);
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      toast.error("That file is over 5 MB; split it into smaller files.");
      return;
    }
    const text = await readText(file);
    setFileName(file.name);
    setCsvText(text);
    await runPreview(text);
  }

  async function onImport() {
    if (!csvText) return;
    try {
      const result = await importLeads.mutateAsync(payload(csvText, false));
      toast.success(importSummary(result));
      reset();
      onOpenChange(false);
    } catch {
      // Error toast already shown.
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Import leads from a file</DialogTitle>
          <DialogDescription>
            Upload the CSV you downloaded from Facebook/Instagram Lead Center, LinkedIn Lead Gen Forms, TikTok, or any spreadsheet.
            Columns like name, email, phone, company and username are matched automatically; other columns are saved as a note on
            each lead. Leads already in the CRM (same email or lead id) are skipped.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-3">
          <FormField label="Platform" htmlFor="import-platform" hint="Used when the file has no platform column.">
            <Select value={platform} onValueChange={(v) => setPlatform(v as SocialPlatform | typeof NOT_SOCIAL)}>
              <SelectTrigger id="import-platform" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SOCIAL_PLATFORMS.map((p) => (
                  <SelectItem key={p} value={p}>
                    <PlatformIcon platform={p} /> {PLATFORM_LABELS[p]}
                  </SelectItem>
                ))}
                <SelectItem value={NOT_SOCIAL}>Not from social media</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Lead score (0–100)" htmlFor="import-score" error={scoreValid ? undefined : "0–100"}>
            <Input id="import-score" inputMode="numeric" value={score} onChange={(e) => setScore(e.target.value)} />
          </FormField>
          {isManager && (
            <FormField label="Assign to" htmlFor="import-owner">
              <UserSelect id="import-owner" value={ownerId ?? user?.id} onChange={setOwnerId} />
            </FormField>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-dashed p-4">
          <input
            ref={fileInput}
            type="file"
            accept=".csv,.tsv,.txt,text/csv,text/tab-separated-values"
            className="hidden"
            onChange={(e) => onFile(e.target.files?.[0])}
          />
          <Button variant="outline" onClick={() => fileInput.current?.click()} disabled={importLeads.isPending}>
            <FileUp /> {fileName ? "Choose another file" : "Choose CSV file"}
          </Button>
          <span className="min-w-0 truncate text-sm text-muted-foreground">{fileName ?? "No file selected (max 5,000 rows)"}</span>
          {csvText && (
            <Button variant="ghost" size="sm" onClick={() => runPreview(csvText)} disabled={importLeads.isPending}>
              Refresh preview
            </Button>
          )}
        </div>

        {preview && (
          <div className="grid gap-3">
            <p className="text-sm">
              <span className="font-medium">{preview.created}</span> new lead{preview.created === 1 ? "" : "s"} to import
              {preview.skipped > 0 && <>, {preview.skipped} duplicate{preview.skipped === 1 ? "" : "s"} will be skipped</>}
              {preview.failed > 0 && <>, {preview.failed} row{preview.failed === 1 ? "" : "s"} can&apos;t be read</>}.
            </p>
            {preview.preview.length > 0 && (
              <div className="max-h-56 overflow-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Company</TableHead>
                      <TableHead>Platform</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.preview.map((row, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{row.name}</TableCell>
                        <TableCell>{row.email ?? "—"}</TableCell>
                        <TableCell>{row.phone ?? "—"}</TableCell>
                        <TableCell>{row.company_name ?? "—"}</TableCell>
                        <TableCell>{row.social_platform ? <PlatformIcon platform={row.social_platform} /> : "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
            {preview.issues.length > 0 && (
              <details className="text-sm">
                <summary className="cursor-pointer text-muted-foreground">Rows that won&apos;t be imported</summary>
                <ul className="mt-2 grid max-h-32 gap-1 overflow-auto text-muted-foreground">
                  {preview.issues.map((issue) => (
                    <li key={issue.row}>
                      Row {issue.row}
                      {issue.name ? ` (${issue.name})` : ""}: {issue.reason}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onImport} disabled={!preview || preview.created === 0 || !scoreValid || importLeads.isPending}>
            {importLeads.isPending ? "Working…" : preview ? `Import ${preview.created} lead${preview.created === 1 ? "" : "s"}` : "Import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

import fs from "node:fs/promises";
import path from "node:path";
import initSqlJs, { type Database } from "sql.js";
import type { AuditReport } from "@/lib/audit/types";
import { toJsonReport, toMarkdownReport } from "@/lib/report";

export type StoredJob = {
  id: string;
  status: "passed" | "warned" | "failed";
  report: AuditReport;
  markdown: string;
  rawPaths: {
    dataset: string;
    system: string;
    baseline: string;
    corpus?: string;
    config: string;
  };
  createdAt: string;
};

let dbPromise: Promise<Database> | null = null;

function storageRoot(): string {
  return process.env.AUDIT_STORAGE_DIR ?? path.join(process.cwd(), ".local-audits");
}

function dbPath(): string {
  return path.join(storageRoot(), "jobs.sqlite");
}

async function ensureDirs(): Promise<void> {
  await fs.mkdir(path.join(storageRoot(), "raw"), { recursive: true });
}

async function openDb(): Promise<Database> {
  await ensureDirs();
  const SQL = await initSqlJs();
  let db: Database;
  try {
    const data = await fs.readFile(dbPath());
    db = new SQL.Database(data);
  } catch {
    db = new SQL.Database();
  }
  db.run(`
    CREATE TABLE IF NOT EXISTS audit_jobs (
      id TEXT PRIMARY KEY,
      status TEXT NOT NULL,
      report_json TEXT NOT NULL,
      markdown TEXT NOT NULL,
      raw_paths_json TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
  `);
  return db;
}

async function db(): Promise<Database> {
  dbPromise ??= openDb();
  return dbPromise;
}

async function persist(database: Database): Promise<void> {
  await ensureDirs();
  const data = database.export();
  await fs.writeFile(dbPath(), Buffer.from(data));
}

export function privateRawPath(jobId: string, part: string, extension: string): string {
  const safePart = part.replace(/[^a-z0-9_-]/gi, "");
  const safeExt = extension === ".jsonl" ? ".jsonl" : ".json";
  return path.join(storageRoot(), "raw", `${jobId}-${safePart}${safeExt}`);
}

export async function storeRaw(pathname: string, content: string): Promise<void> {
  const root = path.resolve(storageRoot());
  const target = path.resolve(pathname);
  if (!target.startsWith(root)) throw new Error("Refusing to write outside audit storage.");
  await ensureDirs();
  await fs.writeFile(target, content, { mode: 0o600 });
}

export async function saveJob(job: StoredJob): Promise<void> {
  const database = await db();
  database.run(
    "INSERT OR REPLACE INTO audit_jobs (id, status, report_json, markdown, raw_paths_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
    [job.id, job.status, JSON.stringify(toJsonReport(job.report)), job.markdown, JSON.stringify(job.rawPaths), job.createdAt],
  );
  await persist(database);
}

export async function readStoredRaw(job: StoredJob): Promise<{
  datasetText: string;
  systemText: string;
  baselineText: string;
  corpusText?: string;
  configText: string;
}> {
  const [datasetText, systemText, baselineText, corpusText, configText] = await Promise.all([
    fs.readFile(job.rawPaths.dataset, "utf8"),
    fs.readFile(job.rawPaths.system, "utf8"),
    fs.readFile(job.rawPaths.baseline, "utf8"),
    job.rawPaths.corpus ? fs.readFile(job.rawPaths.corpus, "utf8") : Promise.resolve(undefined),
    fs.readFile(job.rawPaths.config, "utf8"),
  ]);
  return { datasetText, systemText, baselineText, corpusText, configText };
}

export async function getJob(id: string): Promise<StoredJob | null> {
  const database = await db();
  const rows = database.exec("SELECT * FROM audit_jobs WHERE id = ?", [id]);
  const row = rows[0]?.values[0];
  if (!row) return null;
  const report = JSON.parse(String(row[2])) as AuditReport;
  return {
    id: String(row[0]),
    status: row[1] as StoredJob["status"],
    report,
    markdown: String(row[3]),
    rawPaths: JSON.parse(String(row[4])),
    createdAt: String(row[5]),
  };
}

export async function latestJob(): Promise<StoredJob | null> {
  const database = await db();
  const rows = database.exec("SELECT id FROM audit_jobs ORDER BY created_at DESC LIMIT 1");
  const id = rows[0]?.values[0]?.[0];
  return id ? getJob(String(id)) : null;
}

export async function deleteJob(id: string): Promise<boolean> {
  const job = await getJob(id);
  if (!job) return false;
  const database = await db();
  database.run("DELETE FROM audit_jobs WHERE id = ?", [id]);
  await persist(database);
  await Promise.all(Object.values(job.rawPaths).filter((rawPath): rawPath is string => Boolean(rawPath)).map((rawPath) => fs.rm(rawPath, { force: true })));
  return true;
}

export function statusFromVerdict(verdict: AuditReport["verdict"]): StoredJob["status"] {
  if (verdict === "PASS") return "passed";
  if (verdict === "FAIL") return "failed";
  return "warned";
}

export function markdownFor(report: AuditReport): string {
  return toMarkdownReport(report);
}

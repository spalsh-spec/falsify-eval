import { NextRequest, NextResponse } from "next/server";
import { AUDIT_TEMPLATES, getAuditTemplate, templateToYaml } from "@/lib/audit/templates";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ templates: AUDIT_TEMPLATES });
  const template = getAuditTemplate(id);
  return NextResponse.json({ template, yaml: templateToYaml(template) });
}

import { InvestigationsPage } from "@/components/pages/investigations";

type InvestigationPageProps = { searchParams: Promise<{ predictionId?: string | string[] }> };

export default async function InvestigationWorkspacePage({ searchParams }: InvestigationPageProps) {
  const params = await searchParams;
  return <InvestigationsPage initialPredictionId={typeof params.predictionId === "string" ? params.predictionId : undefined} />;
}

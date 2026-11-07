import { AnomalyPage } from "@/components/pages/anomalies";

type AnomalyPageProps = { searchParams: Promise<{ record?: string | string[] }> };

export default async function AnomalyIntelligencePage({ searchParams }: AnomalyPageProps) {
  const params = await searchParams;
  return <AnomalyPage initialRecordId={typeof params.record === "string" ? params.record : undefined} />;
}

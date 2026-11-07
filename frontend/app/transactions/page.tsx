import { TransactionsPage } from "@/components/pages/transactions";

type TransactionPageProps = { searchParams: Promise<{ record?: string | string[] }> };

export default async function TransactionHistoryPage({ searchParams }: TransactionPageProps) {
  const params = await searchParams;
  return <TransactionsPage initialRecordId={typeof params.record === "string" ? params.record : undefined} />;
}

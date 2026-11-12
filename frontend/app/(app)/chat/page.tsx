import { ChatPage } from "@/features/chat/chat-page";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const params = await searchParams;
  return <ChatPage initialPrompt={params.q?.trim() ?? ""} />;
}

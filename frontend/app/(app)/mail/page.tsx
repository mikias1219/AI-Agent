import { StubPage } from "@/components/shell/stub-page";

export default function Page() {
  return (
    <StubPage
      title="Mail"
      intro="Messages AURA has read or drafted for you."
      emptyTitle="Nothing to show yet"
      emptyDescription="Connect Google under Connections and mail activity will appear here. Until then, nothing is shown."
    />
  );
}

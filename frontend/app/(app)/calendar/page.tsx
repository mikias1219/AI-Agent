import { StubPage } from "@/components/shell/stub-page";

export default function Page() {
  return (
    <StubPage
      title="Calendar"
      intro="Your schedule, read from a connected calendar."
      emptyTitle="Nothing to show yet"
      emptyDescription="Connect Google under Connections and AURA will show events here. Until then, nothing is shown."
    />
  );
}

import { RegisterForm } from "@/features/auth/register-form";

export default function RegisterPage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h2
          className="text-xl font-semibold text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Create your account
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Set up the owner for this workspace.</p>
      </header>

      <RegisterForm />
    </div>
  );
}

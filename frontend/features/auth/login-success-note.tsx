"use client";

import { useSearchParams } from "next/navigation";
import { LoginForm } from "./login-form";

export function LoginSuccessNote() {
  const searchParams = useSearchParams();
  const registered = searchParams.get("registered") === "1";
  const successNote = registered ? "Account created. Sign in with your password." : null;

  return <LoginForm successNote={successNote} />;
}

"use client";

import { useId, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { IconButton } from "@/components/ui/icon-button";

export type PasswordFieldProps = {
  label: string;
  name?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  autoComplete?: string;
  disabled?: boolean;
};

export function PasswordField({
  label,
  name = "password",
  value,
  onChange,
  error,
  autoComplete = "current-password",
  disabled,
}: PasswordFieldProps) {
  const id = useId();
  const [visible, setVisible] = useState(false);

  return (
    <Field label={label} htmlFor={id} error={error}>
      <div className="relative">
        <Input
          id={id}
          name={name}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          disabled={disabled}
          className="pr-11"
        />
        <IconButton
          type="button"
          label={visible ? "Hide password" : "Show password"}
          size="sm"
          className="absolute top-1/2 right-1.5 -translate-y-1/2 border-0 bg-transparent hover:bg-[var(--canvas)]"
          onClick={() => setVisible((v) => !v)}
          disabled={disabled}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </IconButton>
      </div>
    </Field>
  );
}

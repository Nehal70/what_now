"use client";

import Link from "next/link";
import { useActionState } from "react";

import {
  savePhoneNumber,
  type PhoneSettingsState,
} from "@/app/settings/phone/actions";

const initialState: PhoneSettingsState = {};

type PhoneSettingsFormProps = {
  defaultPhone?: string;
};

export default function PhoneSettingsForm({
  defaultPhone = "",
}: PhoneSettingsFormProps) {
  const [state, formAction, pending] = useActionState(
    savePhoneNumber,
    initialState,
  );

  return (
    <div className="phone-settings-panel">
      <form action={formAction} className="phone-settings-form">
        <label htmlFor="phone">Your phone number</label>
        <input
          id="phone"
          name="phone"
          type="tel"
          defaultValue={defaultPhone}
          placeholder="+1 (555) 123-4567"
          autoComplete="tel"
          required
        />
        {state.error ? (
          <p className="phone-settings-error" role="alert">
            {state.error}
          </p>
        ) : null}
        {state.success ? (
          <p className="phone-settings-success" role="status">
            {state.success}
          </p>
        ) : null}
        <div className="phone-settings-actions">
          <button
            type="submit"
            className="phone-settings-submit"
            disabled={pending}
          >
            {pending ? "Saving…" : "Save phone number"}
          </button>
          <Link href="/" className="phone-settings-back">
            {state.success ? "Go to dashboard" : "Back to dashboard"}
          </Link>
        </div>
      </form>
    </div>
  );
}

"use client";

import { FIELDS, subfieldsFor } from "@/lib/fields";

type Props = {
  field: string;
  subfield: string;
  /** Called with the new (field, subfield). Subfield resets to "" on field change. */
  onChange: (field: string, subfield: string) => void;
};

const SELECT_CLASS =
  "mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60";

/**
 * Two-level discipline picker (Field → Subfield) shared across the Pipeline,
 * Workflow and Agent Hub run forms. The selection is passed to the backend in
 * the pipeline `constraints` (see `web/src/lib/fields.ts`), where it steers
 * retrieval source routing, outline structure, and drafting prompts.
 */
export default function FieldSelector({ field, subfield, onChange }: Props) {
  const subs = subfieldsFor(field);
  return (
    <>
      <label className="text-sm text-zinc-300">
        Field
        <select
          className={SELECT_CLASS}
          value={field}
          onChange={(e) => onChange(e.target.value, "")}
        >
          {FIELDS.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm text-zinc-300">
        Subfield
        <select
          className={SELECT_CLASS}
          value={subfield}
          onChange={(e) => onChange(field, e.target.value)}
        >
          <option value="">Any / general</option>
          {subs.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

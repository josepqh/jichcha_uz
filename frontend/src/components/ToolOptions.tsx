import { useId } from "react";
import { useTranslation } from "react-i18next";

import { TextField } from "@/components/forms";
import { isFieldVisible, type OptionField, type OptionValues } from "@/lib/tools";

interface Props {
  fields: readonly OptionField[];
  values: OptionValues;
  disabled: boolean;
  errors?: Record<string, string | undefined>;
  onChange: (name: string, value: string) => void;
}

function RadioGroup({ field, values, disabled, onChange }: Omit<Props, "fields" | "errors"> & { field: OptionField }) {
  const { t, i18n } = useTranslation();
  const uid = useId();
  return (
    <fieldset disabled={disabled}>
      <legend className="mb-2 text-sm font-semibold">{t(`options.${field.name}.label`)}</legend>
      <div className="flex flex-wrap gap-2">
        {field.choices?.map((choice) => {
          const id = `${uid}-${choice}`;
          const hintKey = `options.${field.name}.hints.${choice}`;
          const hint = i18n.exists(hintKey) ? t(hintKey) : null;
          return (
            <div key={choice}>
              <input
                id={id}
                type="radio"
                name={`${uid}-${field.name}`}
                value={choice}
                checked={values[field.name] === choice}
                onChange={() => onChange(field.name, choice)}
                className="peer sr-only"
              />
              <label
                htmlFor={id}
                className="flex min-h-11 cursor-pointer flex-col justify-center rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm transition-colors duration-150 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-primary-fg peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-ring peer-disabled:cursor-not-allowed peer-disabled:opacity-50 hover:bg-surface-muted peer-checked:hover:bg-primary-hover"
              >
                <span className="font-semibold">{t(`options.${field.name}.choices.${choice}`)}</span>
                {hint ? <span className="text-xs opacity-80">{hint}</span> : null}
              </label>
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}

export function ToolOptions({ fields, values, disabled, errors = {}, onChange }: Props) {
  const { t } = useTranslation();
  const visible = fields.filter((field) => isFieldVisible(field, values));
  if (visible.length === 0) return null;
  return (
    <div className="space-y-5">
      {visible.map((field) =>
        field.choices ? (
          <RadioGroup key={field.name} field={field} values={values} disabled={disabled} onChange={onChange} />
        ) : (
          <TextField
            key={field.name}
            label={t(`options.${field.name}.label`)}
            hint={t(`options.${field.name}.hint`)}
            placeholder={t(`options.${field.name}.placeholder`)}
            name={field.name}
            value={values[field.name] ?? ""}
            onChange={(e) => onChange(field.name, e.target.value)}
            disabled={disabled}
            error={errors[field.name]}
            autoComplete="off"
            inputMode="text"
            spellCheck={false}
          />
        ),
      )}
    </div>
  );
}

import type { ReactNode } from "react";

import { card } from "@/lib/ui";

export function AuthCard({ title, intro, children, footer }: { title: string; intro?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-md space-y-6">
      <header className="space-y-2 text-center">
        <h1 className="font-display text-3xl leading-[1.1] font-medium tracking-[-0.045em] sm:text-4xl">{title}</h1>
        {intro ? <p className="text-muted text-pretty">{intro}</p> : null}
      </header>
      <div className={`${card} space-y-5 p-5 sm:p-6`}>{children}</div>
      {footer ? <div className="text-center text-sm text-muted">{footer}</div> : null}
    </div>
  );
}

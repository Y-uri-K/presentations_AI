"use client";

import { useCallback, useState } from "react";

import { CreatePresentationPanel } from "@/components/dashboard/CreatePresentationPanel";
import { SavedPresentationsPanel } from "@/components/dashboard/SavedPresentationsPanel";
import { TemplateSelectionProvider } from "@/components/dashboard/TemplateSelectionContext";
import { TemplatesPanel } from "@/components/dashboard/TemplatesPanel";

export function DashboardClient() {
  const [presentationsRefreshSignal, setPresentationsRefreshSignal] = useState(0);
  const refreshPresentations = useCallback(() => {
    setPresentationsRefreshSignal((value) => value + 1);
  }, []);

  return (
    <TemplateSelectionProvider>
      <div className="mt-8">
        <CreatePresentationPanel onPresentationsChanged={refreshPresentations} />
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <SavedPresentationsPanel refreshSignal={presentationsRefreshSignal} />
        <TemplatesPanel />
      </div>
    </TemplateSelectionProvider>
  );
}

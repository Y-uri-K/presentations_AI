"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

import type { TemplateListItem } from "@/lib/api/templates";

type TemplateSelectionContextValue = {
  selectedTemplateId: number | null;
  selectTemplate: (template: TemplateListItem | null) => void;
  selectedTemplate: TemplateListItem | null;
};

const TemplateSelectionContext = createContext<TemplateSelectionContextValue | null>(null);

export function TemplateSelectionProvider({ children }: { children: ReactNode }) {
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateListItem | null>(null);

  function selectTemplate(template: TemplateListItem | null) {
    setSelectedTemplate(template);
  }

  return (
    <TemplateSelectionContext.Provider
      value={{
        selectedTemplateId: selectedTemplate?.id ?? null,
        selectedTemplate,
        selectTemplate,
      }}
    >
      {children}
    </TemplateSelectionContext.Provider>
  );
}

export function useTemplateSelection() {
  const context = useContext(TemplateSelectionContext);
  if (!context) {
    throw new Error("useTemplateSelection must be used within TemplateSelectionProvider");
  }
  return context;
}

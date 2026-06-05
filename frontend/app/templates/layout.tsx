import type { ReactNode } from "react";

import { AuthGuard } from "@/components/auth/AuthGuard";

export default function TemplatesLayout({ children }: { children: ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}

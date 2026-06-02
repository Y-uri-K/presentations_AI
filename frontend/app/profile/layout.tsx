import type { ReactNode } from "react";

import { AuthGuard } from "@/components/auth/AuthGuard";

export default function ProfileLayout({ children }: { children: ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}

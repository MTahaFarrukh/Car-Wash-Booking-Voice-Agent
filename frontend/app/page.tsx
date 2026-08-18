import { HealthStatus } from "@/components/health-status";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-muted/30 px-4 py-16">
      <main className="flex w-full max-w-2xl flex-col items-center gap-8">
        <div className="space-y-3 text-center">
          <span className="inline-flex items-center rounded-full border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
            Phase 1 foundation
          </span>
          <h1 className="text-4xl font-semibold tracking-tight">
            Sparkle AI Receptionist
          </h1>
          <p className="mx-auto max-w-lg text-muted-foreground">
            AI-powered car wash receptionist and booking platform. This landing
            page validates monorepo connectivity — dashboard and booking flows
            arrive in later phases.
          </p>
        </div>

        <HealthStatus />

        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>What&apos;s included</CardTitle>
            <CardDescription>
              Phase 1 delivers the project skeleton only.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>Next.js frontend with Tailwind and shadcn/ui</p>
            <p>FastAPI backend with health endpoints</p>
            <p>SQLAlchemy models and Alembic config (migrations in Phase 2)</p>
          </CardContent>
        </Card>

        <Button variant="outline" size="sm" nativeButton={false} render={<a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" />}>
          Open API docs
        </Button>
      </main>
    </div>
  );
}

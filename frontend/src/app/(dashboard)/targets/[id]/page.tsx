"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { targetsApi } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Globe,
  Server,
  ArrowLeft,
  Shield,
  Trash2,
} from "lucide-react";
import Link from "next/link";

export default function TargetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const targetId = params.id as string;

  const { data: target, isLoading } = useQuery({
    queryKey: ["target", targetId],
    queryFn: () => targetsApi.get(targetId).then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: () => targetsApi.delete(targetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      toast.success("Target deleted");
      router.push("/targets");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Failed to delete target");
    },
  });

  if (isLoading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>;
  }

  if (!target) {
    return <div className="text-center py-12 text-muted-foreground">Target not found</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/targets">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            {target.target_type === "web_application" ? (
              <Globe className="h-8 w-8 text-primary" />
            ) : (
              <Server className="h-8 w-8 text-primary" />
            )}
            {target.hostname}
          </h1>
          <p className="text-muted-foreground capitalize">
            {target.target_type.replace("_", " ")}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={`/scans/new?target=${target.id}`}>
            <Button>
              <Shield className="mr-2 h-4 w-4" />
              Start Scan
            </Button>
          </Link>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => {
              if (confirm("Delete this target? This cannot be undone.")) {
                deleteMutation.mutate();
              }
            }}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Target Info */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Target Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Type</span>
              <span className="text-sm capitalize">
                {target.target_type.replace("_", " ")}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Created</span>
              <span className="text-sm">
                {new Date(target.created_at).toLocaleDateString()}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Scope</CardTitle>
            <CardDescription>Authorized testing scope</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {target.scope?.map((item: string, idx: number) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 rounded border p-2 text-sm font-mono"
                >
                  <Globe className="h-3 w-3 text-muted-foreground" />
                  {item}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

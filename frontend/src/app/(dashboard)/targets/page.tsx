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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import {
  Target,
  Plus,
  Globe,
  Server,
  ExternalLink,
} from "lucide-react";

export default function TargetsPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    hostname: "",
    target_type: "web_application",
    scope: "",
  });

  const { data: targets, isLoading } = useQuery({
    queryKey: ["targets"],
    queryFn: () => targetsApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => targetsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      setShowAdd(false);
      setForm({ hostname: "", target_type: "web_application", scope: "" });
      toast.success("Target added successfully");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Failed to create target");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const scopeItems = form.scope
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    createMutation.mutate({
      hostname: form.hostname,
      target_type: form.target_type,
      scope: scopeItems.length > 0 ? scopeItems : [form.hostname],
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Targets</h1>
          <p className="text-muted-foreground">
            Manage your penetration testing targets
          </p>
        </div>
        <Button onClick={() => setShowAdd(!showAdd)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Target
        </Button>
      </div>

      {/* Add Target Form */}
      {showAdd && (
        <Card>
          <CardHeader>
            <CardTitle>Add New Target</CardTitle>
            <CardDescription>
              Add a target for penetration testing. You&apos;ll need to verify
              ownership before scanning.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-sm font-medium">
                  Hostname / IP
                </label>
                <Input
                  placeholder="example.com or 192.168.1.0/24"
                  value={form.hostname}
                  onChange={(e) =>
                    setForm({ ...form, hostname: e.target.value })
                  }
                  required
                />
              </div>

              <div>
                <label className="text-sm font-medium">Target Type</label>
                <select
                  value={form.target_type}
                  onChange={(e) =>
                    setForm({ ...form, target_type: e.target.value })
                  }
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="web_application">Web Application</option>
                  <option value="network">Network / Infrastructure</option>
                  <option value="api">API</option>
                  <option value="cloud">Cloud Infrastructure</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium">
                  Scope (comma-separated)
                </label>
                <Input
                  placeholder="*.example.com, api.example.com"
                  value={form.scope}
                  onChange={(e) => setForm({ ...form, scope: e.target.value })}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Domains/IPs the scanner is allowed to test. Leave empty to use
                  hostname only.
                </p>
              </div>

              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Creating..." : "Create Target"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAdd(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Target List */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">
          Loading targets...
        </div>
      ) : targets?.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Target className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p className="text-muted-foreground">
              No targets yet. Add your first target to get started.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {targets?.map((target: any) => (
            <Link key={target.id} href={`/targets/${target.id}`}>
              <Card className="hover:bg-muted/30 transition-colors cursor-pointer">
                <CardContent className="flex items-center justify-between p-6">
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                      {target.target_type === "web_application" ? (
                        <Globe className="h-6 w-6 text-primary" />
                      ) : (
                        <Server className="h-6 w-6 text-primary" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-lg">{target.hostname}</p>
                      <p className="text-sm text-muted-foreground capitalize">
                        {target.target_type.replace("_", " ")}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <ExternalLink className="h-4 w-4 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

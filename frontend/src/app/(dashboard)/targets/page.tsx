"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { targetsApi } from "@/lib/api";
import Link from "next/link";
import { useState } from "react";
import { Target, Plus, Globe, Server, Network, ExternalLink, Trash2, Loader2 } from "lucide-react";

const TYPE_ICON: Record<string, React.ElementType> = {
  url: Globe, domain: Globe,
  ip: Server, ip_range: Network,
  web_application: Globe, network: Network, api: Globe,
};

const TYPE_OPTIONS = [
  { value: "url",      label: "Web Application / URL" },
  { value: "domain",   label: "Domain" },
  { value: "ip",       label: "IP-adres (server)" },
  { value: "ip_range", label: "IP-range / Netwerk" },
];

export default function TargetsPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ value: "", target_type: "url", name: "" });
  const [errorMsg, setErrorMsg] = useState("");

  const { data: raw, isLoading } = useQuery({
    queryKey: ["targets"],
    queryFn: () => targetsApi.list().then((r) => r.data),
  });

  // Normalise: backend returns array, guard against other shapes
  const targets: any[] = Array.isArray(raw) ? raw : [];

  const createMutation = useMutation({
    mutationFn: (data: any) => targetsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      setShowAdd(false);
      setForm({ value: "", target_type: "url", name: "" });
      setErrorMsg("");
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      setErrorMsg(
        typeof detail === "string" ? detail :
        Array.isArray(detail) ? detail.map((d: any) => d.msg ?? String(d)).join(", ") :
        "Aanmaken mislukt"
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => targetsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["targets"] }),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    if (!form.value.trim()) { setErrorMsg("Voer een target-adres in"); return; }
    createMutation.mutate({
      value:       form.value.trim(),
      name:        form.name.trim() || form.value.trim(),
      target_type: form.target_type,
      hostname:    form.value.trim(),  // backend accepts either field
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-bold" style={{ letterSpacing: "-0.03em" }}>Targets</h1>
          <p className="text-[15px] text-muted-foreground mt-0.5">Beheer penetratietest doelwitten</p>
        </div>
        <button
          onClick={() => { setShowAdd(!showAdd); setErrorMsg(""); }}
          className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90"
          style={{ background: "#0071e3", color: "#fff" }}
        >
          <Plus className="h-4 w-4" />
          Target toevoegen
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="rounded-2xl border border-border bg-card shadow-apple p-6">
          <h2 className="text-[17px] font-semibold mb-4">Nieuw target</h2>
          {errorMsg && (
            <p className="mb-4 rounded-xl border px-4 py-3 text-[13px]"
               style={{ borderColor: "rgba(255,59,48,0.3)", background: "rgba(255,59,48,0.04)", color: "#ff3b30" }}>
              {errorMsg}
            </p>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium mb-1.5">Adres (URL, IP, domein)</label>
              <input
                type="text"
                placeholder="https://example.com  of  192.168.1.0/24"
                value={form.value}
                onChange={(e) => setForm({ ...form, value: e.target.value })}
                required
                className="w-full rounded-xl border border-border bg-secondary px-4 py-2.5 text-[14px] placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium mb-1.5">Naam (optioneel)</label>
              <input
                type="text"
                placeholder="Bijv. Productie webserver"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-xl border border-border bg-secondary px-4 py-2.5 text-[14px] placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium mb-1.5">Type</label>
              <select
                value={form.target_type}
                onChange={(e) => setForm({ ...form, target_type: e.target.value })}
                className="w-full rounded-xl border border-border bg-secondary px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                {TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90 disabled:opacity-50"
                style={{ background: "#0071e3", color: "#fff" }}
              >
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {createMutation.isPending ? "Aanmaken..." : "Aanmaken"}
              </button>
              <button
                type="button"
                onClick={() => { setShowAdd(false); setErrorMsg(""); }}
                className="rounded-xl border border-border px-5 py-2.5 text-[14px] font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Annuleren
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Target list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground text-[14px]">
          <Loader2 className="h-5 w-5 animate-spin mr-2" /> Laden...
        </div>
      ) : targets.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card shadow-apple p-16 text-center">
          <Target className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4" />
          <p className="text-[17px] font-semibold mb-2">Nog geen targets</p>
          <p className="text-[14px] text-muted-foreground mb-6">
            Voeg je eerste target toe om een penetratietest te starten.
          </p>
          <button
            onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90"
            style={{ background: "#0071e3", color: "#fff" }}
          >
            <Plus className="h-4 w-4" /> Target toevoegen
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {targets.map((target: any) => {
            const Icon = TYPE_ICON[target.target_type] ?? Server;
            const display = target.hostname ?? target.value ?? target.name ?? "—";
            return (
              <div
                key={target.id}
                className="rounded-2xl border border-border bg-card shadow-apple hover:shadow-apple-md transition-shadow"
              >
                <div className="flex items-center justify-between p-5">
                  <Link href={`/targets/${target.id}`} className="flex items-center gap-4 min-w-0 flex-1">
                    <div className="h-11 w-11 rounded-xl flex items-center justify-center flex-shrink-0"
                         style={{ background: "rgba(0,113,227,0.08)" }}>
                      <Icon className="h-5 w-5" style={{ color: "#0071e3" }} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-[15px] font-semibold truncate">{display}</p>
                      <p className="text-[13px] text-muted-foreground mt-0.5 capitalize">
                        {(target.target_type ?? "").replace(/_/g, " ")}
                        {target.is_verified && (
                          <span className="ml-2 text-[11px] font-medium"
                                style={{ color: "#34c759" }}>✓ Geverifieerd</span>
                        )}
                      </p>
                    </div>
                  </Link>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    <Link href={`/scans/new?target=${target.id}`}
                      className="rounded-lg border border-border px-3 py-1.5 text-[12px] font-medium text-muted-foreground hover:text-foreground transition-colors">
                      Scan starten
                    </Link>
                    <button
                      onClick={() => deleteMutation.mutate(target.id)}
                      disabled={deleteMutation.isPending}
                      className="h-8 w-8 rounded-lg flex items-center justify-center transition-colors hover:bg-secondary text-muted-foreground hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <ExternalLink className="h-4 w-4 text-muted-foreground/40" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { Customer } from "@/types";
import { Button } from "@/components/ui/button";

export default function AdminCustomersPage() {
  const [rows, setRows] = useState<Customer[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.listCustomers({ limit: 200 });
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Failed to load customers");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function load(search = q) {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.listCustomers({ q: search || undefined, limit: 200 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load customers");
    } finally {
      setLoading(false);
    }
  }
  async function create() {
    setCreating(true);
    setError(null);
    try {
      await api.createCustomer({ name: name.trim(), phone: phone.trim() });
      setName("");
      setPhone("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl font-bold">Customers</h1>
      <div className="flex flex-wrap gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search"
          className="rounded-lg border border-input px-3 py-2 text-sm"
        />
        <Button onClick={() => void load()}>Search</Button>
      </div>
      <div className="flex flex-wrap gap-2 rounded-xl border border-border bg-white p-4">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          className="rounded-lg border border-input px-3 py-2 text-sm"
        />
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="Phone"
          className="rounded-lg border border-input px-3 py-2 text-sm"
        />
        <Button disabled={creating || !name.trim() || !phone.trim()} onClick={() => void create()}>
          Create customer
        </Button>
      </div>
      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {!loading && rows.length === 0 && <p className="text-sm text-muted-foreground">No customers found.</p>}
      <div className="overflow-x-auto rounded-xl border border-border bg-white">
        <table className="min-w-full text-sm">
          <thead className="border-b bg-foam text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Phone</th>
              <th className="px-3 py-2 text-left">Email</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">{row.name}</td>
                <td className="px-3 py-2">{row.phone}</td>
                <td className="px-3 py-2">{row.email ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

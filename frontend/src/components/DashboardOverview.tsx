import { useEffect, useState } from 'react';

interface DashboardStats {
  total_transactions: number;
  fraud_detected: number;
  amount_at_risk: number;
  active_investigations: number;
}

export default function DashboardOverview() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    fetch('/api/v1/dashboard/stats')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error("API error", err));
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4">
      <div className="bg-card text-card-foreground p-6 rounded-xl border border-border shadow-sm">
        <h3 className="text-sm font-medium text-muted-foreground">Total Transactions</h3>
        <div className="text-2xl font-bold mt-2">{stats?.total_transactions || 0}</div>
      </div>
      <div className="bg-card text-card-foreground p-6 rounded-xl border border-border shadow-sm">
        <h3 className="text-sm font-medium text-muted-foreground">Fraud Detected</h3>
        <div className="text-2xl font-bold mt-2 text-destructive">{stats?.fraud_detected || 0}</div>
      </div>
      <div className="bg-card text-card-foreground p-6 rounded-xl border border-border shadow-sm">
        <h3 className="text-sm font-medium text-muted-foreground">Amount At Risk</h3>
        <div className="text-2xl font-bold mt-2">${stats?.amount_at_risk || 0}</div>
      </div>
      <div className="bg-card text-card-foreground p-6 rounded-xl border border-border shadow-sm">
        <h3 className="text-sm font-medium text-muted-foreground">Active Investigations</h3>
        <div className="text-2xl font-bold mt-2 text-accent-foreground">{stats?.active_investigations || 0}</div>
      </div>
    </div>
  );
}

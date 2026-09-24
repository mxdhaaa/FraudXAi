import { useState, useEffect } from 'react';

interface Transaction {
  id: string;
  channel: string;
  amount: number;
  sender_id: string;
  city?: string | null;
  country?: string | null;
  risk_score?: {
    risk_score: number;
    risk_level: string;
    recommended_action: string;
  } | null;
}

export default function TransactionExplorer() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  useEffect(() => {
    fetch('/api/v1/transactions')
      .then(res => res.json())
      .then(data => setTransactions(data))
      .catch(err => console.error("API error", err));
  }, []);

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Transaction Explorer</h2>
      <div className="overflow-x-auto border border-border rounded-lg shadow-sm">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted text-muted-foreground border-b border-border">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Channel</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Sender</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Risk Score</th>
              <th className="px-4 py-3">Decision</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-4 text-muted-foreground">
                  No transactions available.
                </td>
              </tr>
            ) : (
              transactions.map((txn) => (
                <tr key={txn.id} className="border-b border-border hover:bg-muted/50 cursor-pointer">
                  <td className="px-4 py-3 font-mono">{txn.id.substring(0, 8)}...</td>
                  <td className="px-4 py-3">{txn.channel}</td>
                  <td className="px-4 py-3">${txn.amount.toFixed(2)}</td>
                  <td className="px-4 py-3">{txn.sender_id}</td>
                  <td className="px-4 py-3">{[txn.city, txn.country].filter(Boolean).join(', ') || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      txn.risk_score?.risk_level === 'CRITICAL' ? 'bg-destructive text-destructive-foreground' : 
                      txn.risk_score?.risk_level === 'HIGH' ? 'bg-orange-500 text-white' : 'bg-primary/20 text-primary'
                    }`}>
                      {txn.risk_score ? txn.risk_score.risk_score.toFixed(1) : 'N/A'}
                    </span>
                  </td>
                  <td className="px-4 py-3">{txn.risk_score?.recommended_action || 'PENDING'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

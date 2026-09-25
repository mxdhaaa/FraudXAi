import { useEffect, useMemo, useState } from 'react'
import './App.css'

type Risk = 'LOW' | 'MEDIUM' | 'HIGH'
type RiskFactor = {
  feature: string
  value: number
  impact: number
  direction: string
  description: string
}

type Transaction = {
  id: string
  type: string
  amount: number
  probability: number
  score: number
  risk: Risk
  action: string
  riskFactors?: RiskFactor[]
}

const demoTransactions: Transaction[] = [
  {
    id: 'TEST-FRAUD-005',
    type: 'TRANSFER',
    amount: 59951.61,
    probability: 89.03,
    score: 89.03,
    risk: 'MEDIUM',
    action: 'REVIEW',
  },
]

const rupees = (value: number) => `₹${value.toLocaleString('en-IN')}`
const navigation = ['Dashboard', 'Transactions', 'Investigations', 'Models', 'API'] as const
type Page = typeof navigation[number]

const pageFromHash = (): Page => {
  const route = window.location.hash.replace('#/', '').toLowerCase()
  return navigation.find((page) => page.toLowerCase() === route) ?? 'Dashboard'
}

function App() {
  const [active, setActive] = useState<Page>(pageFromHash)
  const [selected, setSelected] = useState<Transaction>(demoTransactions[0])
  const [transactions, setTransactions] = useState<Transaction[]>(demoTransactions)
  const [humanDecision, setHumanDecision] = useState<string | null>(null)
  const updateCase = async (status: string) => {
  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/v1/cases/${selected?.id}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ status }),
      }
    )

    if (!response.ok) {
      throw new Error('Failed to update case')
    }

    setHumanDecision(status)
  } catch (error) {
    console.error(error)
  }
}
  const [stats, setStats] = useState({ total_transactions: 1005, fraud_detected: 2, amount_at_risk: 14500, active_investigations: 3 })
  const [apiLive, setApiLive] = useState(false)

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/v1/dashboard/stats').then((r) => {
      if (!r.ok) throw new Error('offline')
      return r.json()
    }).then((data) => { setStats({ ...data, active_investigations: data.active_investigations || 3 }); setApiLive(true) }).catch(() => setApiLive(false))
  }, [])
  useEffect(() => {
  fetch('http://127.0.0.1:8000/api/v1/transactions')
    .then((r) => {
      if (!r.ok) throw new Error('transactions offline')
      return r.json()
    })
    .then((data) => {
      if (Array.isArray(data) && data.length > 0) {
        const mapped: Transaction[] = data.map((txn: any) => {
          const risk = txn.risk_score

          return {
  id: txn.id,
  type: txn.channel,
  amount: txn.amount,
  probability: Number(risk?.fraud_probability ?? 0) * 100,
  score: Number(risk?.risk_score ?? 0),
  risk: risk?.risk_level ?? 'LOW',
  action: risk?.recommended_action ?? 'APPROVE',
  riskFactors: risk?.risk_factors ?? [],
}
        })
      setTransactions(mapped)
        setSelected(mapped[0])
      }
    })
    .catch(() => {
      // Keep the existing demo transaction if the API is unavailable.
    })
}, [])


  useEffect(() => {
    const syncRoute = () => setActive(pageFromHash())
    window.addEventListener('hashchange', syncRoute)
    return () => window.removeEventListener('hashchange', syncRoute)
  }, [])

  const goTo = (page: Page) => { window.location.hash = `/${page.toLowerCase()}` }

  const pageTitle = useMemo(() => active === 'Dashboard' ? 'TRANSACTION RISK COMMAND CENTER' : active.toUpperCase(), [active])
  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="#/dashboard" onClick={() => goTo('Dashboard')}><span className="brand-mark">◈</span><div><strong>FRAUDSHIELD <em>AI</em></strong><small>AI-Powered Transaction Risk Intelligence</small></div></a>
      <nav>{navigation.map((item) => <a className={active === item ? 'nav-active' : ''} href={`#/${item.toLowerCase()}`} key={item}>{item}</a>)}</nav>
      <div className="system"><i /> SYSTEM OPERATIONAL</div>
    </header>

    <main>
      <section className="hero-row">
        <div><p className="eyebrow">◉ LIVE RISK INTELLIGENCE</p><h1>{pageTitle}</h1><p className="subtitle">Real-time intelligence for detecting, investigating and preventing financial fraud.</p></div>
        <button className="analyze" onClick={() => goTo('Transactions')}>✦ Analyze Transaction</button>
      </section>
      {!apiLive && <div className="demo-banner">DEMO MODE <span>— Using sample transaction data</span></div>}

      {active === 'Dashboard' && <>
      <section className="metrics">
       <Metric label="TOTAL TRANSACTIONS" value={(stats.total_transactions ?? 0).toLocaleString('en-IN')} trend="↗ +12.4% today" icon="◫" />
        <Metric label="FRAUD DETECTED" value={stats.fraud_detected} trend="● +2 flagged" icon="◉" danger />
        <Metric label="AMOUNT AT RISK" value={rupees(stats.amount_at_risk)} trend="↗ 8.2% monitored" icon="₹" warning />
        <Metric label="ACTIVE INVESTIGATIONS" value={stats.active_investigations} trend="● analyst queue" icon="◎" />
      </section>

      <section className="content-grid">
        <div className="panel overview"><PanelHead title="Transaction Risk Overview" detail="DEMO • Last 24 hours" /><div className="chart-legend"><span><b className="dot cyan" /> Risk score</span><span><b className="dot blue" /> Transaction volume</span></div><div className="chart"><div className="grid-lines" /> <svg viewBox="0 0 760 200" preserveAspectRatio="none"><defs><linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#25d9ff" stopOpacity=".35"/><stop offset="1" stopColor="#25d9ff" stopOpacity="0"/></linearGradient></defs><path d="M0 160 C45 148 80 172 118 128 S185 140 225 105 S290 140 332 95 S400 115 442 62 S510 95 550 75 S620 88 665 35 S720 50 760 18 L760 200 L0 200Z" fill="url(#fill)"/><path d="M0 160 C45 148 80 172 118 128 S185 140 225 105 S290 140 332 95 S400 115 442 62 S510 95 550 75 S620 88 665 35 S720 50 760 18" fill="none" stroke="#25d9ff" strokeWidth="3"/></svg><div className="axis"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>NOW</span></div></div></div>
        <div className="panel distribution"><PanelHead title="Risk Distribution" detail="DEMO SAMPLE" /><div className="donut"><div><strong>1,005</strong><small>TRANSACTIONS</small></div></div><div className="risk-list"><span><b className="dot teal" /> LOW <em>68%</em></span><span><b className="dot amber" /> MEDIUM <em>22%</em></span><span><b className="dot red" /> HIGH <em>10%</em></span></div></div>
      </section>

      <section className="panel activity"><PanelHead title="Recent Suspicious Activity" detail="DEMO / SAMPLE TRANSACTIONS" /><div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Type</th><th>Amount</th><th>Fraud Probability</th><th>Risk Score</th><th>Risk Level</th><th>Action</th></tr></thead><tbody>{demoTransactions.map((txn) => <tr onClick={() => setSelected(txn)} className={selected.id === txn.id ? 'selected' : ''} key={txn.id}><td><span className="txn-icon">◈</span>{txn.id}</td><td>{txn.type}</td><td>{rupees(txn.amount)}</td><td><div className="prob"><span style={{ width: `${txn.probability}%` }} />{txn.probability}%</div></td><td><strong>{txn.score}</strong></td><td><Badge risk={txn.risk} /></td><td><span className={`action ${txn.action.toLowerCase()}`}>{txn.action}</span></td></tr>)}</tbody></table></div></section>

      <section className="detail-grid">
        <div className="panel detail"><PanelHead title={`Transaction $selected?.id`} detail="SELECTED • DEMO" /><div className="detail-stats"><div><small>Amount</small><strong>{rupees(selected.amount)}</strong></div><div><small>Fraud Probability</small><strong className="danger-text">{selected.probability}%</strong></div><div><small>Risk Score</small><strong>{selected.score} <small>/ 100</small></strong></div><div><small>Risk Level</small><Badge risk={selected.risk} /></div></div><p className="meter-label">RISK INTENSITY <b>{selected.score}/100</b></p><div className="risk-meter"><span style={{ width: `${selected.score}%` }} /></div><div className="factor-box"><p>WHY WAS THIS FLAGGED?</p><ul><li>Unusually high transaction amount</li><li>Strong fraud-classifier signal</li><li>Transaction appears anomalous</li><li>Multiple risk indicators detected</li></ul></div><p className="recommend">RECOMMENDED ACTION <strong>{selected.action}</strong></p><div className="actions"><button className="block">BLOCK TRANSACTION</button><button>SEND FOR REVIEW</button><button>MARK AS SAFE</button></div><small className="demo-note">Demo controls only — no financial transaction is changed.</small></div>
        <div className="panel pipeline"><PanelHead title="AI Risk Engine" detail="ALL MODELS ACTIVE" />{['Transaction received', 'XGBoost fraud classifier', 'Isolation Forest anomaly detector', 'Risk engine fusion', 'Decision recommendation'].map((step, i) => <div className="pipe-step" key={step}><span>{i + 1}</span><div><strong>{step}</strong><small>{i === 0 ? 'Channel, amount & behaviour signals' : i === 4 ? 'Approve • Review • Block' : 'ACTIVE • Real-time inference'}</small></div>{i < 4 && <i>↓</i>}</div>)}<div className="api-status"><b>●</b> BACKEND {apiLive ? 'CONNECTED' : 'DEMO MODE'}<span>● DATABASE READY</span></div></div>
      </section>
      </>}
      {active !== 'Dashboard' && (
  <PageView
    active={active}
    transactions={transactions}
    selected={selected}
    onSelect={setSelected}
    apiLive={apiLive}
    humanDecision={humanDecision}
    updateCase={updateCase}
  />
)}le
    </main>
  </div>
}

function PageView({
  active,
  transactions,
  selected,
  onSelect,
  apiLive,
  humanDecision,
  updateCase,
}: {
  active: Exclude<Page, 'Dashboard'>
  transactions: Transaction[]
  selected: Transaction
  onSelect: (transaction: Transaction) => void
  apiLive: boolean
  humanDecision: string | null
  updateCase: (status: string) => void
}) {
 if (active === 'Transactions') {
  return (
    <section className="route-view">
      <div className="panel activity">
        <PanelHead
          title="Transaction Explorer"
          detail="LIVE API WHEN AVAILABLE"
        />

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Fraud Probability</th>
                <th>Risk Score</th>
                <th>Risk Level</th>
                <th>Recommended Action</th>
              </tr>
            </thead>

            <tbody>
              {transactions.map((txn) => (
                <tr
                  className={selected?.id === txn.id ? 'selected' : ''}
                  onClick={() => onSelect(txn)}
                  key={txn.id}
                >
                  <td>{txn.id}</td>
                  <td>{txn.type}</td>
                  <td>{rupees(txn.amount)}</td>
                  <td>{txn.probability}%</td>
                  <td>{txn.score} / 100</td>
                  <td>
                    <Badge risk={txn.risk} />
                  </td>
                  <td>
                    <span className={`action ${txn.action.toLowerCase()}`}>
                      {txn.action}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="panel detail route-detail">
          <PanelHead
            title={`Transaction ${selected.id}`}
            detail="SELECT A ROW TO INVESTIGATE"
          />

          <div className="detail-stats">
            <div>
              <small>Amount</small>
              <strong>{rupees(selected.amount)}</strong>
            </div>

            <div>
              <small>Fraud Probability</small>
              <strong className="danger-text">
                {selected.probability}%
              </strong>
            </div>

            <div>
              <small>Risk Score</small>
              <strong>{selected.score.toFixed(2)} / 100</strong>
            </div>

            <div>
              <small>Recommended Action</small>
              <strong>{selected.action}</strong>
            </div>
          </div>

          <p className="meter-label">
            RISK INTENSITY <b>{selected.score}/100</b>
          </p>

          <div className="risk-meter">
            <span style={{ width: `${selected.score}%` }} />
          </div>
          <div className="shap-panel">
  <PanelHead
    title="WHY THIS SCORE?"
    detail="SHAP MODEL EXPLANATION"
  />

  {selected.riskFactors && selected.riskFactors.length > 0 ? (
    <div className="shap-list">
      {selected.riskFactors.map((factor, index) => (
        <div className="shap-factor" key={`${factor.feature}-${index}`}>
          <div>
            <strong>{factor.feature}</strong>
            <small>{factor.description}</small>
          </div>

          <span>
            {factor.impact > 0 ? '+' : ''}
            {Number(factor.impact).toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  ) : (
    <p>No explanation data available.</p>
  )}
</div>
        </div>
      )}
    </section>
  )
}
  if (active === 'Investigations') {
  return (
    <section className="route-view">
      <div className="panel activity">
        <PanelHead
          title="Open Investigations"
          detail="HUMAN-IN-THE-LOOP CASE MANAGEMENT"
        />

        <div className="investigation-list">
          {transactions
            .filter((txn) => txn.action === 'REVIEW')
            .map((txn, index) => (
              <button
                className={selected?.id === txn.id ? 'case selected' : 'case'}
                onClick={() => onSelect(txn)}
                key={txn.id}
              >
                <span className="case-num">
                  {String(index + 1).padStart(2, '0')}
                </span>

                <div>
                  <strong>{txn.id}</strong>
                  <small>
                    AI recommendation: Human investigation required
                  </small>
                </div>

                <Badge risk={txn.risk} />

                <span className={`action ${txn.action.toLowerCase()}`}>
                  {txn.action}
                </span>
              </button>
            ))}
        </div>
      </div>

      {selected && (
        <div className="panel detail route-detail">
          <PanelHead
            title={`Investigation: ${selected.id}`}
            detail="HUMAN DECISION REQUIRED"
          />

          <div className="detail-stats">
            <div>
              <small>Risk Score</small>
              <strong>{selected.score.toFixed(2)}/100</strong>
            </div>

            <div>
              <small>Fraud Probability</small>
              <strong>{selected.probability.toFixed(2)}%</strong>
            </div>

            <div>
              <small>AI Recommendation</small>
              <strong>{selected.action}</strong>
            </div>

            <div>
              <small>Status</small>
              <strong className="danger-text">OPEN</strong>
            </div>
          </div>

          <div className="factor-box">
            <p>MODEL EVIDENCE</p>

            <ul>
              {selected.riskFactors?.map((factor, index) => (
                <li key={`${factor.feature}-${index}`}>
                  <strong>{factor.feature}</strong> — {factor.description}
                  {' '}
                  ({factor.impact > 0 ? '+' : ''}
                  {factor.impact.toFixed(2)} SHAP)
                </li>
              ))}
            </ul>
          </div>

          <div className="factor-box">
            <p>HUMAN DECISION</p>

            <button
  className="action review"
  onClick={() => updateCase('CONFIRMED_FRAUD')}
>
  CONFIRM FRAUD
</button>
            <button
  className="action approve"
  onClick={() => updateCase('CONFIRMED_LEGITIMATE')}
>
              CONFIRM LEGITIMATE
            </button>

            <button
  className="action review"
 onClick={() => updateCase('ESCALATED')}
>
  ESCALATE
</button>

{humanDecision && (
  <p>
    HUMAN DECISION RECORDED: <strong>{humanDecision}</strong>
  </p>
)}
          </div>
        </div>
      )}
    </section>
  )
}
  if (active === 'Models') return <section className="route-view"><div className="model-grid">{[['XGBoost','Fraud Classifier','99.8% classification confidence'],['Isolation Forest','Anomaly Detector','Multivariate pattern analysis'],['Risk Engine','Decision Intelligence','Signals fused into a 0–100 score']].map(([name, type, note]) => <div className="panel model-card" key={name}><span>● ACTIVE</span><h2>{name}</h2><strong>{type}</strong><p>{note}</p></div>)}</div><div className="panel pipeline route-detail"><PanelHead title="Fraud Decision Pipeline" detail="REAL-TIME INFERENCE" />{['Transaction', 'XGBoost', 'Isolation Forest', 'Risk Engine', 'Risk Score', 'Decision'].map((step, index) => <div className="pipe-step" key={step}><span>{index + 1}</span><div><strong>{step}</strong><small>{index === 5 ? 'APPROVE • REVIEW • BLOCK' : 'ACTIVE PROCESSING STAGE'}</small></div>{index < 5 && <i>↓</i>}</div>)}</div></section>
  return <section className="route-view"><div className="panel api-page"><PanelHead title="System Status" detail={apiLive ? 'LIVE HEALTH CHECK' : 'DEMO MODE'} />{[['Backend', apiLive ? 'ONLINE' : 'DEMO MODE'],['Database', apiLive ? 'ONLINE' : 'DEMO MODE'],['ML Model', apiLive ? 'ONLINE' : 'DEMO MODE'],['Frontend', 'ONLINE']].map(([name, status]) => <div className="status-row" key={name}><span><i className={status === 'ONLINE' ? 'online' : 'demo'} />{name}</span><strong>{status}</strong><small>{status === 'ONLINE' ? 'Operational and responding' : 'Sample data is enabled'}</small></div>)}</div></section>
}

function Metric({ label, value, trend, icon, danger, warning }: { label: string; value: string | number; trend: string; icon: string; danger?: boolean; warning?: boolean }) { return <div className={`metric ${danger ? 'metric-danger' : ''} ${warning ? 'metric-warning' : ''}`}><div className="metric-top"><span>{label}</span><i>{icon}</i></div><strong>{value}</strong><small>{trend}</small></div> }
function PanelHead({ title, detail }: { title: string; detail: string }) { return <div className="panel-head"><h2>{title}</h2><span>{detail}</span></div> }
function Badge({ risk }: { risk: Risk }) { return <span className={`badge ${risk.toLowerCase()}`}>{risk}</span> }
export default App

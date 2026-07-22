import Link from "next/link";

const workflow = [
  ["New customer requests", "Incoming tickets"],
  ["Review and assign each request", "Triage"],
  ["General support / Specialist support", "Level 1 / Level 2"],
  ["Verify the response", "Quality check"],
  ["Complete the request or handle it again", "Resolved / rework"],
] as const;

export default function Home() {
  return <main className="site-shell"><header className="masthead"><Link className="wordmark" href="/">OpsTwin</Link><span className="edition">Support operations</span></header><section className="landing-hero" aria-labelledby="page-title"><div><p className="eyebrow">A fictional support-team scenario</p><h1 id="page-title">Customers are waiting too long for support. Test two possible fixes before changing the real operation.</h1><p className="lede">OpsTwin simulates a fictional customer-support team and compares two possible improvements: adding another general support agent or reviewing and assigning new requests faster. It shows how each change affects waiting time, resolution time, and team workload.</p><div className="landing-actions"><Link className="primary-link" href="/workspace">Try the guided comparison <span aria-hidden="true">&rarr;</span></Link><Link className="secondary-link" href="/workspace?mode=advanced">Open advanced workspace</Link></div></div><aside className="decision-note"><p className="kicker">What you will do</p><ol><li>Review the current support operation</li><li>Compare two possible changes</li><li>Read the observed result and its evidence</li></ol><p>OpsTwin reports comparative simulation evidence. It does not prescribe a decision.</p></aside></section><section className="workflow-section" aria-labelledby="workflow-title"><div><p className="eyebrow">The support process</p><h2 id="workflow-title">How a customer request moves through the team</h2></div><ol className="workflow-rail">{workflow.map(([primary, technical], index) => <li key={technical}><span>{String(index + 1).padStart(2, "0")}</span><strong>{primary}</strong><small>Industry term: {technical}</small></li>)}</ol></section></main>;
}

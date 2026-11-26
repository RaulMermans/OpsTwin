import { useEffect, useState } from "react";
import { invoke, view } from "@forge/bridge";

export function App() {
  const [identity, setIdentity] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([invoke("getLabIdentity"), view.getContext()])
      .then(([lab, context]) => {
        if (!cancelled) {
          setIdentity({
            ...lab,
            moduleType: context?.extension?.type ?? null,
          });
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "The lab identity could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={{ fontFamily: "ui-sans-serif, system-ui, sans-serif", padding: "24px", maxWidth: "720px" }}>
      <p style={{ letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "12px", color: "#44546F" }}>
        Development integration — CG-0
      </p>
      <h1 style={{ margin: "8px 0 4px" }}>OpsTwin for Jira</h1>
      <h2 style={{ margin: "0 0 16px", fontWeight: 500, color: "#172B4D" }}>AI Transformation Lab</h2>
      <p>Simulate before you automate. This page is the CG-0 installability foundation, not the final product surface.</p>
      {error ? <p role="alert">{error}</p> : null}
      {identity ? (
        <dl>
          <dt>Project</dt>
          <dd>{identity.projectKey ?? "not provided by Forge context"}</dd>
          <dt>Module</dt>
          <dd>{identity.moduleType ?? "unknown"}</dd>
          <dt>Signed-in invocation</dt>
          <dd>{identity.accountIdPresent ? "yes" : "no"}</dd>
        </dl>
      ) : (
        <p>Loading lab identity…</p>
      )}
    </main>
  );
}

import {
  API_HEALTH_ENDPOINT,
  API_HEALTH_RESPONSE_EXAMPLE,
} from "../src/api-health";
import {
  getArtifactById,
  getLineageSummary,
  getRightsGateState,
  M01_REVIEW_SNAPSHOT,
  type ImpactReviewItem,
  type LineageSummaryEntry,
} from "../src/m01-review-view-model";

const healthResponse = JSON.stringify(API_HEALTH_RESPONSE_EXAMPLE, null, 2);
const selectedArtifact = getArtifactById(
  M01_REVIEW_SNAPSHOT,
  M01_REVIEW_SNAPSHOT.selectedArtifactId,
);
const lineage = getLineageSummary(M01_REVIEW_SNAPSHOT);

function artifactLabel(artifactId: string): string {
  return getArtifactById(M01_REVIEW_SNAPSHOT, artifactId)?.label ?? artifactId;
}

function lineageList(entries: readonly LineageSummaryEntry[]) {
  if (entries.length === 0) {
    return <p className="empty-state">No direct records in this neighborhood.</p>;
  }

  return (
    <ul className="lineage-list">
      {entries.map((entry) => (
        <li key={`${entry.relation}-${entry.artifactId}`}>
          <span className="lineage-node">{entry.label}</span>
          <span className="lineage-relation">{entry.relation}</span>
        </li>
      ))}
    </ul>
  );
}

function impactStatus(item: ImpactReviewItem) {
  return (
    <div className="impact-status-stack">
      <span className={`status-badge status-${item.classification}`}>
        {item.classification}
      </span>
      <span className="resolution-text">
        Resolution: <strong>{item.resolutionStatus}</strong>
      </span>
    </div>
  );
}

export default function HomePage() {
  const rightsAsset = M01_REVIEW_SNAPSHOT.assets[0];
  const rightsGate = rightsAsset ? getRightsGateState(rightsAsset) : undefined;

  return (
    <main className="page-shell">
      <header className="hero" aria-labelledby="page-title">
        <p className="eyebrow">M01 · Canon, lineage, impact, rights</p>
        <h1 id="page-title">Film Production Graph</h1>
        <p className="hero-title">Foundation Lite review studio</p>
        <p className="lede">
          A compact review surface for immutable artifact snapshots and their
          dependencies. This is a deterministic presentation fixture, not a
          live database view.
        </p>
        <div className="snapshot-notice" role="note">
          <strong>Offline review snapshot.</strong> No API request or canon
          mutation is made by this page, its build, or its smoke tests.
        </div>
      </header>

      <section className="panel" aria-labelledby="canon-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">M01 exit path</p>
            <h2 id="canon-title">M01 canon overview</h2>
          </div>
          <span className="status-badge status-locked">Snapshot only</span>
        </div>
        <p className="section-intro">
          The required foundation artifacts are represented as locked,
          immutable versions. A locked payload is never edited in place; a
          revision creates a new version.
        </p>
        <div className="table-wrap">
          <table className="data-table canon-table">
            <caption className="sr-only">Locked M01 canon artifacts</caption>
            <thead>
              <tr>
                <th scope="col">Artifact</th>
                <th scope="col">Schema</th>
                <th scope="col">Revision</th>
                <th scope="col">Lifecycle</th>
                <th scope="col">Content hash</th>
              </tr>
            </thead>
            <tbody>
              {M01_REVIEW_SNAPSHOT.artifacts.map((artifact) => (
                <tr key={artifact.id}>
                  <th scope="row">{artifact.label}</th>
                  <td>{artifact.schemaVersion}</td>
                  <td>v{artifact.revision}</td>
                  <td>
                    <span className="status-badge status-locked">
                      {artifact.lifecycleStatus} · immutable
                    </span>
                  </td>
                  <td>
                    <code className="hash" title={artifact.contentHash}>
                      {artifact.contentHash.slice(0, 16)}…
                    </code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="authority-note">
          Approval and lock transitions are <strong>human-only</strong>.
          Agents may propose artifacts, patches, or findings, but this studio
          grants no agent approval authority.
        </p>
      </section>

      <section className="panel" aria-labelledby="lineage-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Selected neighborhood</p>
            <h2 id="lineage-title">Bidirectional lineage</h2>
          </div>
          <span className="selected-chip">
            Selected: {selectedArtifact?.label ?? "Unknown artifact"}
          </span>
        </div>
        <p className="section-intro">
          Incoming and outgoing edges stay visible together so a reviewer can
          trace both directions without opening a full graph canvas.
        </p>
        <div className="lineage-grid">
          <article className="lineage-card" aria-labelledby="upstream-title">
            <p className="eyebrow">Dependencies feeding this artifact</p>
            <h3 id="upstream-title">Incoming / upstream</h3>
            {lineageList(lineage.upstream)}
          </article>
          <article className="lineage-card" aria-labelledby="downstream-title">
            <p className="eyebrow">Artifacts derived from this artifact</p>
            <h3 id="downstream-title">Outgoing / downstream</h3>
            {lineageList(lineage.downstream)}
          </article>
        </div>
      </section>

      <section className="panel" aria-labelledby="impact-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Review inbox</p>
            <h2 id="impact-title">Impact review inbox</h2>
          </div>
          <span className="status-badge status-possibly_stale">3 records</span>
        </div>
        <p className="section-intro">
          Impact records describe possible upstream consequences; they are
          separate from artifact lifecycle. Resolving an impact never silently
          changes the affected artifact&apos;s lifecycle status.
        </p>
        <div className="impact-key" aria-label="Impact state legend">
          <span>
            <strong>Classification</strong> what the validator or reviewer found
          </span>
          <span>
            <strong>Resolution</strong> what review should happen next
          </span>
        </div>
        <div className="table-wrap">
          <table className="data-table impact-table">
            <caption className="sr-only">M01 impact review records</caption>
            <thead>
              <tr>
                <th scope="col">Impact state</th>
                <th scope="col">Cause → affected</th>
                <th scope="col">Reason</th>
              </tr>
            </thead>
            <tbody>
              {M01_REVIEW_SNAPSHOT.impacts.map((item) => (
                <tr key={item.id}>
                  <td>{impactStatus(item)}</td>
                  <td>
                    <span className="impact-path">
                      {artifactLabel(item.causeArtifactId)}
                      <span aria-hidden="true"> → </span>
                      {artifactLabel(item.affectedArtifactId)}
                    </span>
                    <span className="human-review-label">Human review only</span>
                  </td>
                  <td>{item.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel" aria-labelledby="rights-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Release guard</p>
            <h2 id="rights-title">Asset rights gate</h2>
          </div>
          {rightsGate ? (
            <span className="status-badge status-blocked">
              Rights-blocked · {rightsGate.label}
            </span>
          ) : null}
        </div>
        <p className="section-intro">
          Every asset needs a populated rights record before approval review. A
          complete <strong>declared</strong> or <strong>cleared</strong> record
          opens that review gate; release remains a separate check requiring
          cleared rights for the intended use and territory.
        </p>
        {rightsAsset && rightsGate ? (
          <div className="rights-card">
            <div>
              <p className="eyebrow">Asset under review</p>
              <h3>{rightsAsset.label}</h3>
              <p className="muted">Intended use: {rightsAsset.intendedUse}</p>
            </div>
            <dl className="rights-list">
              <div>
                <dt>Rights status</dt>
                <dd>
                  <span className="status-badge status-blocked">
                    {rightsAsset.rights.status} ·{" "}
                    {rightsGate.complete ? "complete" : "unverified / incomplete"}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Source / holder</dt>
                <dd>
                  {rightsAsset.rights.sourceType} · {rightsAsset.rights.holder}
                </dd>
              </div>
              <div>
                <dt>Permitted uses</dt>
                <dd>{rightsAsset.rights.permittedUses.join(", ")}</dd>
              </div>
              <div>
                <dt>Territories</dt>
                <dd>{rightsAsset.rights.territories.join(", ")}</dd>
              </div>
            </dl>
            <p className="blocked-note" role="status">
              <strong>Rights-blocked state: {rightsGate.label}.</strong>{" "}
              {rightsGate.explanation}{" "}
              Human review is required before this asset can be approved.
            </p>
          </div>
        ) : null}
      </section>

      <section className="panel health-panel" aria-labelledby="health-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Integration contract</p>
            <h2 id="health-title">API health</h2>
          </div>
          <span className="status-badge status-ready">Contract ready</span>
        </div>
        <dl className="contract-list">
          <div>
            <dt>Endpoint</dt>
            <dd>
              <code>{`GET ${API_HEALTH_ENDPOINT}`}</code>
            </dd>
          </div>
          <div>
            <dt>Expected response</dt>
            <dd>
              <pre aria-label="Expected API health response">{healthResponse}</pre>
            </dd>
          </div>
        </dl>
        <p className="note" role="status">
          Offline-safe preview: no API request is made during build or smoke
          tests.
        </p>
      </section>

      <footer className="page-footer">
        <p>
          M01 presentation fixture · Canonical state remains server-side and
          immutable.
        </p>
      </footer>
    </main>
  );
}

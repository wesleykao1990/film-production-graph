import {
  API_HEALTH_ENDPOINT,
  API_HEALTH_RESPONSE_EXAMPLE,
} from "../src/api-health";

const healthResponse = JSON.stringify(API_HEALTH_RESPONSE_EXAMPLE, null, 2);

export default function HomePage() {
  return (
    <main className="page-shell">
      <header className="hero" aria-labelledby="page-title">
        <p className="eyebrow">M00 · Foundation Lite</p>
        <h1 id="page-title">Film Production Graph</h1>
        <p className="hero-title">Foundation Lite review studio</p>
        <p className="lede">
          A small, accessible starting point for story-first production. This
          smoke page is rendered on the server and keeps its contract preview
          deterministic until the API is connected.
        </p>
      </header>

      <section className="panel" aria-labelledby="health-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Integration contract</p>
            <h2 id="health-title">API health</h2>
          </div>
          <span className="status-badge">Contract ready</span>
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
        <p>Production canon remains server-side; this surface is presentation only.</p>
      </footer>
    </main>
  );
}

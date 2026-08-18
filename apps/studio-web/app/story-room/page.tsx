import {
  M04A_ADMIN_REVIEW_FIXTURE,
  formatElapsedTime,
  getRaterFacingProjection,
  type ArtifactReviewStatus,
  type ForcedChoice,
  type ScoredChoice,
} from "../../src/m04a-review-view-model";

const adminReview = M04A_ADMIN_REVIEW_FIXTURE;
const raterReview = getRaterFacingProjection(adminReview);

function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function statusLabel(status: string): string {
  if (status === "passed") return "PASS";
  if (status === "needs_review") return "NEEDS REVIEW";
  if (status === "human_review") return "HUMAN REVIEW";
  if (status === "not_selected") return "NOT SELECTED";
  return status.toUpperCase();
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`m04a-status m04a-status-${status}`}>
      {statusLabel(status)}
    </span>
  );
}

function CandidateCardView({
  candidate,
}: {
  candidate: (typeof adminReview.candidates)[number];
}) {
  return (
    <article
      className={`m04a-candidate-card ${
        candidate.reviewStatus === "selected" ? "m04a-candidate-selected" : ""
      }`}
      aria-label={`${candidate.label} candidate`}
    >
      <div className="m04a-card-topline">
        <h3>{candidate.label}</h3>
        <StatusBadge status={candidate.reviewStatus} />
      </div>
      <p className="m04a-logline">{candidate.logline}</p>
      <p className="m04a-mini-label">Strengths to inspect</p>
      <ul className="m04a-tight-list">
        {candidate.strengths.map((strength) => (
          <li key={strength}>{strength}</li>
        ))}
      </ul>
      <p className="m04a-open-question">
        <strong>Open question:</strong> {candidate.openQuestion}
      </p>
    </article>
  );
}

function ArtifactStatusRow({ artifact }: { artifact: ArtifactReviewStatus }) {
  return (
    <tr>
      <th scope="row">{artifact.label}</th>
      <td>{artifact.versionLabel}</td>
      <td>
        <StatusBadge status={artifact.validation} />
      </td>
      <td>
        <StatusBadge status={artifact.approval} />
      </td>
      <td>{artifact.detail}</td>
    </tr>
  );
}

function SampleCard({
  sample,
}: {
  sample: (typeof raterReview.triplet.samples)[number];
}) {
  return (
    <article className="m04a-sample-card">
      <h3>{sample.displayLabel}</h3>
      <p>{sample.excerpt}</p>
    </article>
  );
}

function ChoiceLabel({
  choice,
  id,
  name,
  forced,
}: {
  choice: ScoredChoice | ForcedChoice;
  id: string;
  name: string;
  forced: boolean;
}) {
  return (
    <label className="m04a-choice" htmlFor={id}>
      <input id={id} name={name} type="radio" value={choice} />
      <span>{choice === "tie" ? "Tie" : humanize(choice)}</span>
      {forced && choice === "left" ? <span className="sr-only"> sample</span> : null}
    </label>
  );
}

function ScoredPairQuestion({
  pair,
  index,
}: {
  pair: (typeof raterReview.triplet.pairs)[number];
  index: number;
}) {
  const groupName = `scored-comparison-${index}`;
  return (
    <fieldset className="m04a-rating-fieldset">
      <legend>
        <span className="m04a-question-index">Question {index + 1}</span>
        {pair.prompt}
      </legend>
      <div className="m04a-pair-preview">
        <article>
          <h3>Left · {pair.leftSample.displayLabel}</h3>
          <p>{pair.leftSample.excerpt}</p>
        </article>
        <article>
          <h3>Right · {pair.rightSample.displayLabel}</h3>
          <p>{pair.rightSample.excerpt}</p>
        </article>
      </div>
      <div className="m04a-choice-row" role="group" aria-label={`${pair.prompt} response`}>
        {pair.choices.map((choice) => (
          <ChoiceLabel
            key={choice}
            choice={choice}
            id={`${groupName}-${choice}`}
            name={groupName}
            forced={false}
          />
        ))}
      </div>
    </fieldset>
  );
}

function ForcedChoiceQuestion({
  item,
  index,
}: {
  item: (typeof raterReview.comparisonTask.dimensions)[number];
  index: number;
}) {
  const groupName = `forced-comparison-${index}`;
  return (
    <fieldset className="m04a-rating-fieldset m04a-comparison-fieldset">
      <legend>
        <span className="m04a-question-index">Comparison question {index + 1}</span>
        {item.prompt}
      </legend>
      <div className="m04a-pair-preview">
        <article>
          <h3>Left · {item.leftSample.displayLabel}</h3>
          <p>{item.leftSample.excerpt}</p>
        </article>
        <article>
          <h3>Right · {item.rightSample.displayLabel}</h3>
          <p>{item.rightSample.excerpt}</p>
        </article>
      </div>
      <div className="m04a-choice-row" role="group" aria-label={`${item.prompt} response`}>
        {item.choices.map((choice) => (
          <ChoiceLabel
            key={choice}
            choice={choice}
            id={`${groupName}-${choice}`}
            name={groupName}
            forced
          />
        ))}
      </div>
    </fieldset>
  );
}

function WorkloadMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="m04a-workload-metric">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export default function StoryRoomPage() {
  const elapsed = formatElapsedTime(raterReview.assignment.elapsedSeconds);
  const decision = adminReview.decision;

  return (
    <main className="page-shell m04a-page">
      <header className="hero m04a-hero" aria-labelledby="m04a-title">
        <p className="eyebrow">M04a · Minimum Story Room gate</p>
        <h1 id="m04a-title">Story Room review</h1>
        <p className="hero-title">Candidate comparison and blinded rating</p>
        <p className="lede">
          {adminReview.projectLabel} · {adminReview.briefLabel}. This deterministic surface
          demonstrates the review and measurement boundary without making a live
          request or writing a rating.
        </p>
        <div className="snapshot-notice" role="note">
          <strong>Offline fixture.</strong> Labels are opaque to the rater. This
          page shows only the material needed to rate each comparison. Nothing
          is persisted.
        </div>
      </header>

      <section className="panel" aria-labelledby="candidate-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Human selection record</p>
            <h2 id="candidate-title">Compare premise candidates</h2>
          </div>
          <span className="status-badge status-ready">3 branches</span>
        </div>
        <p className="section-intro">
          Each branch is shown together with its strengths and open question.
          The selected branch remains a human decision; alternatives remain
          visible for inspection.
        </p>
        <div className="m04a-candidate-grid">
          {adminReview.candidates.map((candidate, index) => (
            <CandidateCardView key={`candidate-${index}`} candidate={candidate} />
          ))}
        </div>
        <aside className="m04a-rationale" aria-labelledby="rationale-title">
          <div className="m04a-card-topline">
            <div>
              <p className="m04a-mini-label">Recorded selection rationale</p>
              <h3 id="rationale-title">
                {adminReview.candidates.find(
                  (candidate) => candidate.reviewStatus === "selected",
                )?.label ?? "Selected candidate"}
              </h3>
            </div>
            <span className="m04a-human-only">Human-only decision</span>
          </div>
          <p>{adminReview.selection.rationale}</p>
          <p className="m04a-meta-line">
            Recorded by <strong>{adminReview.selection.recordedBy}</strong> ·{" "}
            {adminReview.selection.recordedAt}
          </p>
          <p className="m04a-presentation-note">{adminReview.selection.presentationNote}</p>
        </aside>
      </section>

      <section className="panel" aria-labelledby="artifact-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Artifact inspector</p>
            <h2 id="artifact-title">Validation and approval status</h2>
          </div>
          <span className="status-badge status-ready">Review snapshot</span>
        </div>
        <p className="section-intro">
          Validation is shown separately from approval. Agents can surface
          findings, while approval remains a human review step.
        </p>
        <div className="table-wrap">
          <table className="data-table m04a-artifact-table">
            <caption className="sr-only">M04a artifact validation and approval statuses</caption>
            <thead>
              <tr>
                <th scope="col">Artifact</th>
                <th scope="col">Version</th>
                <th scope="col">Validation</th>
                <th scope="col">Approval</th>
                <th scope="col">Review detail</th>
              </tr>
            </thead>
            <tbody>
              {adminReview.artifacts.map((artifact, index) => (
                <ArtifactStatusRow key={`artifact-${index}`} artifact={artifact} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel" aria-labelledby="triplet-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Scored task · opaque labels</p>
            <h2 id="triplet-title">Matched comparison task</h2>
          </div>
          <span className="status-badge status-locked">Blinded</span>
        </div>
        <p className="section-intro">{raterReview.triplet.instructions}</p>
        <div className="m04a-sample-grid" aria-label="Opaque samples in this matched triplet">
          {raterReview.triplet.samples.map((sample, index) => (
            <SampleCard key={`sample-${index}`} sample={sample} />
          ))}
        </div>
        <div className="m04a-rating-list">
          {raterReview.triplet.pairs.map((pair, index) => (
            <ScoredPairQuestion key={`pair-${index}`} pair={pair} index={index} />
          ))}
        </div>
        <p className="m04a-rating-note" role="note">
          Scored dimensions permit left, right, or tie. This page only presents
          responses; it does not submit or persist the selected response.
        </p>
      </section>

      <section className="panel" aria-labelledby="comparison-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Instrument validity · forced choice</p>
            <h2 id="comparison-title">Comparison task</h2>
          </div>
          <StatusBadge status={adminReview.instrument.status} />
        </div>
        <p className="section-intro">{raterReview.comparisonTask.instructions}</p>
        <div className="m04a-rating-list">
          {raterReview.comparisonTask.dimensions.map((item, index) => (
            <ForcedChoiceQuestion key={`comparison-${index}`} item={item} index={index} />
          ))}
        </div>
        <div className="m04a-technical-action" role="note">
          <div>
            <strong>Technical issue with this comparison?</strong>
            <p>
              Abort and replace the task before the dataset is frozen. A
              technical defect is not a scored preference and is never included
              in the scored dataset.
            </p>
          </div>
          <button type="button" className="m04a-secondary-button">
            {raterReview.comparisonTask.technicalProblemAction}
          </button>
        </div>
      </section>

      <section className="panel" aria-labelledby="workload-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Assignment and workload</p>
            <h2 id="workload-title">Rater progress</h2>
          </div>
          <span className="selected-chip">Task progress</span>
        </div>
        <dl className="m04a-workload-grid">
          <WorkloadMetric label="Task" value={raterReview.assignment.taskPosition} />
          <WorkloadMetric
            label="Completed"
            value={`${raterReview.assignment.completedTaskCount} of ${raterReview.assignment.totalTaskCount}`}
          />
          <WorkloadMetric
            label="Elapsed"
            value={`${raterReview.assignment.elapsedLabel} (${elapsed})`}
          />
          <WorkloadMetric
            label="Target"
            value={`≤ ${raterReview.assignment.targetMinutes} minutes`}
          />
          <WorkloadMetric
            label="Judgments per triplet"
            value={String(raterReview.assignment.scoredJudgmentsPerTriplet)}
          />
        </dl>
        <p className="m04a-workload-note">
          Keep all three judgments per scored triplet. If the target is not
          reachable, the protocol calls for a workload-approved assignment
          change—not fewer judgments.
        </p>
      </section>

      <section className="panel m04a-decision-panel" aria-labelledby="decision-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Decision inspection</p>
            <h2 id="decision-title">Gate outcome: {decision.label}</h2>
          </div>
          <span className="m04a-status m04a-status-inconclusive">{decision.status}</span>
        </div>
        <div className="m04a-decision-callout" role="status" aria-live="polite">
          <strong>{decision.summary}</strong>
        </div>
        {decision.status === "INCONCLUSIVE" ? (
          <div className="m04a-withheld" role="note">
            <h3>Preference results withheld</h3>
            <p>
              No scored preference values are displayed because the measurement
              check failed. Repair the measurement instrument under a new
              protocol before inspecting any preference result.
            </p>
          </div>
        ) : (
          <div className="m04a-decision-values">
            <h3>Preference values available to authorized analysis</h3>
            {decision.preferenceResults.length > 0 ? (
              <ul>
                {decision.preferenceResults.map((result) => (
                  <li key={result.dimension}>
                    {humanize(result.dimension)}: {result.displayedValue}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No preference values in this fixture.</p>
            )}
          </div>
        )}
        <p className="m04a-presentation-note">
          {adminReview.instrument.summary} The gate status shown here is a
          presentation fixture, not a live decision record.
        </p>
      </section>

      <footer className="page-footer">
        M04a offline review surface · server-rendered fixture · no API request,
        write, or persistence operation
      </footer>
    </main>
  );
}

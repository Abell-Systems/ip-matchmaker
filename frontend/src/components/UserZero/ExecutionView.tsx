import type { JobProgress, PipelineStage } from "../../types/patent";
import styles from "./ExecutionView.module.css";

interface ExecutionViewProps {
  domain: string;
  stage: PipelineStage;
  progress?: JobProgress;
}

export function ExecutionView({ domain, stage, progress }: ExecutionViewProps) {
  const stagesList = [
    {
      id: "researching",
      label: "Research patent landscape",
      metric: progress?.patentsAnalyzed ? `${progress.patentsAnalyzed.toLocaleString()} patents` : null,
    },
    {
      id: "clustering",
      label: "Find white-space",
      metric: progress?.clustersFound ? `${progress.clustersFound} opportunities` : null,
    },
    {
      id: "inventing",
      label: "Generate inventions",
      metric: progress?.candidatesGenerated ? `${progress.candidatesGenerated} candidates` : null,
    },
    {
      id: "adversarial",
      label: "Prior-art challenge",
      metric:
        progress?.candidatesRejected !== undefined || progress?.candidatesSurvived !== undefined
          ? `${progress?.candidatesRejected ?? 0} rejected / ${progress?.candidatesRevised ?? 0} revised / ${progress?.candidatesSurvived ?? 0} survived`
          : null,
    },
    {
      id: "governor",
      label: "Final assessment",
      metric: stage === "governor" || stage === "done" ? "Scores & evidence" : null,
    },
  ];

  const stageOrder: PipelineStage[] = [
    "queued",
    "researching",
    "clustering",
    "inventing",
    "adversarial",
    "governor",
    "done",
  ];

  const currentIdx = stageOrder.indexOf(stage);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h2 className={styles.domainTitle}>{domain}</h2>
      </header>

      <div className={styles.pipeline}>
        {stagesList.map((st) => {
          const stIdx = stageOrder.indexOf(st.id as PipelineStage);
          let stateClass = styles.pending;
          let icon = "○";

          if (stIdx < currentIdx || stage === "done") {
            stateClass = styles.completed;
            icon = "✓";
          } else if (stIdx === currentIdx) {
            stateClass = styles.active;
            icon = "●";
          }

          return (
            <div key={st.id} className={`${styles.stepRow} ${stateClass}`}>
              <span className={styles.icon}>{icon}</span>
              <span className={styles.label}>{st.label}</span>
              <span className={styles.metric}>{st.metric || ""}</span>
            </div>
          );
        })}
      </div>

      <footer className={styles.notice}>
        <p>The agent is working autonomously.</p>
      </footer>
    </div>
  );
}

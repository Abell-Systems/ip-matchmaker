import styles from "./BrandHeader.module.css";

interface BrandHeaderProps {
  domain?: string | null;
}

export function AbellMark({ size = 34 }: { size?: number }) {
  return (
    <svg
      className={styles.logoMark}
      style={{ width: size, height: size }}
      viewBox="0 0 48 48"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="abell-gradient" x1="8" y1="8" x2="40" y2="40">
          <stop offset="0%" stopColor="#8b5cf6" />
          <stop offset="55%" stopColor="#6d5dfc" />
          <stop offset="100%" stopColor="#4f7cff" />
        </linearGradient>
      </defs>
      <path
        d="M27.6 4 10.2 25.2c-1.2 1.5-.2 3.8 1.8 3.8h9.2l-3.2 15.1c-.4 2.1 2.2 3.2 3.4 1.5L38 23.9c1.2-1.6.1-3.9-1.9-3.9h-9.2l3.9-12.9C31.5 4.8 29.1 2.6 27.6 4Z"
        fill="url(#abell-gradient)"
      />
    </svg>
  );
}

export function BrandHeader({ domain }: BrandHeaderProps) {
  return (
    <div className={styles.row}>
      <div className={styles.brand}>
        <AbellMark />
        <span className={styles.brandName}>
          ABELL <strong>SYSTEMS</strong>
        </span>
      </div>
      {domain && <div className={styles.domainBadge}>{domain}</div>}
    </div>
  );
}

import styles from './Skeleton.module.css';

export function Skeleton({ width = '100%', height = 16, radius = 8, style }) {
  return <span className={styles.skeleton} style={{ width, height, borderRadius: radius, ...style }} />;
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className={styles.errorBox} role="alert">
      <p className={styles.errorText}>{message || 'Something went wrong while loading your referral data.'}</p>
      {onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export default Skeleton;

import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, History } from 'lucide-react';
import { getReferrals, getRewardHistory } from '../../api/referrals';
import { useReferral } from '../../context/ReferralContext';
import EmptyState from '../common/EmptyState';
import Skeleton, { ErrorState } from '../common/Skeleton';
import styles from './ReferralList.module.css';

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'successful', label: 'Successful' },
  { id: 'pending', label: 'Pending' },
  { id: 'spam', label: 'Spam' },
];

const STATUS_CLASS = {
  SUCCESSFUL: styles.success,
  QUALIFYING: styles.pending,
  PENDING: styles.pending,
  SPAM: styles.spam,
  REJECTED: styles.spam,
  FRAUD_REVIEW: styles.review,
};

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function ReferralList() {
  const { status: authStatus } = useReferral();
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (authStatus !== 'ready') return;
    setLoading(true);
    setError(null);
    try {
      const [list, rewards] = await Promise.all([
        getReferrals({ page, limit: 5, status: filter }),
        getRewardHistory({ page: 1, limit: 6 }),
      ]);
      setResult(list);
      setHistory(rewards.items ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [authStatus, filter, page]);

  useEffect(() => {
    load();
  }, [load]);

  const items = result?.items ?? [];
  const totalPages = result?.totalPages ?? 1;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Your Referrals</h2>
          <p className={styles.subtitle}>Paginated, server-filtered and privacy-masked</p>
        </div>
        <div className={styles.filters}>
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={filter === f.id ? styles.filterActive : styles.filter}
              onClick={() => {
                setFilter(f.id);
                setPage(1);
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorState message={error.message} onRetry={load} />}

      {loading && !error && (
        <div className={styles.rows}>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} height={62} radius={14} />
          ))}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="Nothing here yet"
          description="Referrals matching this filter will appear here once your friends join."
        />
      )}

      {!loading && !error && items.length > 0 && (
        <>
          <div className={styles.rows}>
            {items.map((item, index) => (
              <motion.div
                key={item.id}
                className={styles.row}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <div className={styles.rowMain}>
                  <span className={styles.friend}>{item.referredUser ?? 'Pending registration'}</span>
                  <span className={styles.meta}>Joined {formatDate(item.createdAt)}</span>
                </div>
                <div className={styles.rowProgress}>
                  <span className={styles.ads}>
                    {item.adsWatched} / {item.adsRequired} ads
                  </span>
                  <div className={styles.miniTrack}>
                    <span
                      className={styles.miniFill}
                      style={{
                        width: `${Math.min(100, Math.round((item.adsWatched / Math.max(item.adsRequired, 1)) * 100))}%`,
                      }}
                    />
                  </div>
                </div>
                <span className={`${styles.badge} ${STATUS_CLASS[item.status] ?? ''}`}>
                  {item.status === 'FRAUD_REVIEW' ? 'UNDER REVIEW' : item.status}
                </span>
              </motion.div>
            ))}
          </div>

          <div className={styles.pagination}>
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              aria-label="Previous page"
            >
              <ChevronLeft size={16} />
            </button>
            <span>
              Page {result?.page ?? 1} of {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              aria-label="Next page"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </>
      )}

      {history.length > 0 && (
        <div className={styles.history}>
          <h3 className={styles.historyTitle}>
            <History size={16} /> Referral Reward History
          </h3>
          <ul className={styles.historyList}>
            {history.map((txn) => (
              <li key={txn.id}>
                <span className={styles.amount}>
                  +{txn.amount.toLocaleString('en-IN')} {txn.rewardType}
                </span>
                <span className={styles.reason}>{txn.reason}</span>
                <span className={styles.date}>{formatDate(txn.createdAt)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default ReferralList;

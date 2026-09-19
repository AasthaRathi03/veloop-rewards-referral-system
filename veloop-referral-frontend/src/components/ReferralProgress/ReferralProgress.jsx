import { motion } from 'framer-motion';
import { Trophy, Target, Megaphone } from 'lucide-react';
import { useReferral } from '../../context/ReferralContext';
import Skeleton from '../common/Skeleton';
import styles from './ReferralProgress.module.css';
import CoinScatterBackground from '../common/CoinScatterBackground';

/**
 * Ad-watch progress of the referred friend closest to their next milestone.
 * current / target / percent / next reward all come from the backend.
 */
function ReferralProgress() {
  const { data, isLoading } = useReferral();
  const progress = data?.referralProgress;

  const current = progress?.adsWatched ?? 0;
  const target = progress?.adsRequired ?? 0;
  const percent = progress?.percent ?? 0;
  const remaining = progress?.adsRemaining ?? 0;
  const nextReward = progress?.nextReward;

  return (
    <motion.div
      className={styles.panel}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.6 }}
    >
      <CoinScatterBackground />

      <motion.div
        className={styles.megaphoneWrap}
        animate={{ scale: [1, 1.18, 1], rotate: [0, -8, 0] }}
        transition={{ duration: 0.6, repeat: Infinity, repeatDelay: 1.4, ease: 'easeInOut' }}
        aria-hidden="true"
      >
        <Megaphone size={22} />
        <motion.span
          className={styles.pulseRing}
          animate={{ scale: [1, 1.8], opacity: [0.5, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, repeatDelay: 1.2, ease: 'easeOut' }}
        />
      </motion.div>

      <div className={styles.top}>
        <div className={styles.titleGroup}>
          <div className={styles.iconBadge}>
            <Target size={20} />
          </div>
          <div>
            <h3 className={styles.title}>Referral Progress</h3>
            {isLoading ? (
              <Skeleton width={220} height={14} />
            ) : (
              <p className={styles.subtitle}>
                {!progress?.referralId
                  ? 'Invite a friend to start tracking ad-watch progress'
                  : remaining > 0
                    ? `${remaining} more eligible ads to unlock ${nextReward?.label ?? 'your next reward'}`
                    : 'All milestones reached!'}
              </p>
            )}
          </div>
        </div>

        <div className={styles.rewardChip}>
          <Trophy size={16} />
          <span>{nextReward?.label ?? 'All unlocked'}</span>
        </div>
      </div>

      <div className={styles.barTrack}>
        <motion.div
          className={styles.barFill}
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
        />
        <motion.div
          className={styles.barGlowDot}
          initial={{ left: '0%', opacity: 0 }}
          animate={{ left: `${percent}%`, opacity: 1 }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
        />
      </div>

      <div className={styles.bottom}>
        <span className={styles.countLabel}>
          <strong>{current}</strong> / {target} ads
          {progress?.referredUser ? ` · ${progress.referredUser}` : ''}
        </span>
        <span className={styles.percentLabel}>{percent}%</span>
      </div>
    </motion.div>
  );
}

export default ReferralProgress;

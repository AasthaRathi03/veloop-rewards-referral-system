import { motion } from 'framer-motion';
import { Trophy, Target, Megaphone } from 'lucide-react';
import { referralInfo, rewards } from '../../utils/dummyData';
import styles from './ReferralProgress.module.css';
import CoinScatterBackground from '../common/CoinScatterBackground';

function getNextMilestone(current) {
  const upcoming = rewards
    .filter((r) => r.requiredTasks > 0)
    .sort((a, b) => a.requiredTasks - b.requiredTasks)
    .find((r) => r.requiredTasks > current);
  return upcoming || rewards[rewards.length - 1];
}

function ReferralProgress() {
  const current = referralInfo.totalReferrals;
  const nextMilestone = getNextMilestone(current);
  const target = nextMilestone.requiredTasks || current;
  const percent = Math.min(100, Math.round((current / target) * 100));
  const remaining = Math.max(0, target - current);

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
        transition={{
          duration: 0.6,
          repeat: Infinity,
          repeatDelay: 1.4,
          ease: 'easeInOut',
        }}
        aria-hidden="true"
      >
        <Megaphone size={22} />
        <motion.span
          className={styles.pulseRing}
          animate={{ scale: [1, 1.8], opacity: [0.5, 0] }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            repeatDelay: 1.2,
            ease: 'easeOut',
          }}
        />
      </motion.div>

      <div className={styles.top}>
        <div className={styles.titleGroup}>
          <div className={styles.iconBadge}>
            <Target size={20} />
          </div>
          <div>
            <h3 className={styles.title}>Next Milestone</h3>
            <p className={styles.subtitle}>
              {remaining > 0
                ? `${remaining} more referrals to unlock ${nextMilestone.title}`
                : 'Milestone reached!'}
            </p>
          </div>
        </div>

        <div className={styles.rewardChip}>
          <Trophy size={16} />
          <span>{nextMilestone.title}</span>
        </div>
      </div>

      <div className={styles.barTrack}>
        <motion.div
          className={styles.barFill}
          initial={{ width: 0 }}
          whileInView={{ width: `${percent}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
        />
        <motion.div
          className={styles.barGlowDot}
          initial={{ left: '0%', opacity: 0 }}
          whileInView={{ left: `${percent}%`, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
        />
      </div>

      <div className={styles.bottom}>
        <span className={styles.countLabel}>
          <strong>{current}</strong> / {target} referrals
        </span>
        <span className={styles.percentLabel}>{percent}%</span>
      </div>
    </motion.div>
  );
}

export default ReferralProgress;
import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useMotionValue, useTransform, animate } from 'framer-motion';
import { Users, CheckCircle2, Clock, Coins, Zap, Gem, ShieldAlert, Sparkles } from 'lucide-react';
import { useReferral } from '../../context/ReferralContext';
import FloatingOrbs from '../common/FloatingOrbs';
import FloatingRewardIcons from '../common/FloatingRewardIcons';
import EmptyState from '../common/EmptyState';
import CoinScatterBackground from '../common/CoinScatterBackground';
import Skeleton, { ErrorState } from '../common/Skeleton';
import styles from './StatsSection.module.css';

const ICONS = {
  total: Users,
  success: CheckCircle2,
  pending: Clock,
  spam: ShieldAlert,
  earnings: Coins,
  xp: Zap,
  gems: Gem,
  tokens: Sparkles,
};

const ACCENTS = {
  total: 'indigo',
  success: 'emerald',
  pending: 'amber',
  spam: 'rose',
  earnings: 'gold',
  xp: 'teal',
  gems: 'rose',
  tokens: 'indigo',
};

/** Every stat below is read straight from GET /api/referrals/me. */
function buildStats(data) {
  if (!data) return [];
  return [
    { id: 'total', label: 'Total Referrals', value: data.totalReferrals },
    { id: 'success', label: 'Successful Referrals', value: data.successfulReferrals },
    { id: 'pending', label: 'Pending Referrals', value: data.pendingReferrals },
    { id: 'spam', label: 'Spam Referrals', value: data.spamReferrals },
    { id: 'earnings', label: 'Total SVE Earned', value: data.totalSvesEarned, unit: 'SVE' },
    { id: 'tokens', label: 'Total Tokens Earned', value: data.totalTokensEarned },
    { id: 'xp', label: 'Total XP Earned', value: data.totalXpEarned },
    { id: 'gems', label: 'Total Gems Earned', value: data.totalGemsEarned },
  ];
}

function Counter({ value }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-40px' });
  const motionVal = useMotionValue(0);
  const rounded = useTransform(motionVal, (latest) => Math.round(latest).toLocaleString('en-IN'));
  const [display, setDisplay] = useState('0');

  useEffect(() => {
    if (!isInView) return undefined;
    const controls = animate(motionVal, value, { duration: 1.4, ease: 'easeOut' });
    const unsubscribe = rounded.on('change', (v) => setDisplay(v));
    return () => {
      controls.stop();
      unsubscribe();
    };
  }, [isInView, value, motionVal, rounded]);

  return <span ref={ref}>{display}</span>;
}

function StatBar({ stat, index }) {
  const Icon = ICONS[stat.id];
  const accent = ACCENTS[stat.id];

  return (
    <motion.div
      className={`${styles.card} ${styles[accent]}`}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.4, delay: index * 0.06 }}
    >
      <div className={styles.iconWrap}>
        <Icon size={20} />
      </div>
      <div className={styles.textCol}>
        <div className={styles.value}>
          <Counter value={stat.value} />
          {stat.unit && <span className={styles.unit}> {stat.unit}</span>}
        </div>
        <div className={styles.label}>{stat.label}</div>
      </div>
    </motion.div>
  );
}

function StatsSection() {
  const { data, status, error, refresh, isLoading } = useReferral();
  const stats = buildStats(data);
  const hasReferrals = (data?.totalReferrals ?? 0) + (data?.spamReferrals ?? 0) > 0;

  return (
    <div className={styles.panel} id="stats">
      <CoinScatterBackground />
      <FloatingOrbs />
      <FloatingRewardIcons
        items={[
          { type: 'coin', top: '5%', left: '6%', size: 44, delay: 0.2, duration: 4.5 },
          { type: 'diamond', top: '12%', left: '90%', size: 40, delay: 0.5, duration: 5 },
          { type: 'bitcoin', top: '70%', left: '4%', size: 38, delay: 0.4, duration: 4.8 },
          { type: 'coin', top: '80%', left: '92%', size: 36, delay: 0.7, duration: 5.2 },
        ]}
      />

      <motion.div
        className={styles.header}
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
      >
        <h2 className={styles.title}>Your Referral Stats</h2>
        <p className={styles.subtitle}>Live figures from your VELOOP rewards ledger</p>
      </motion.div>

      {status === 'error' && <ErrorState message={error?.message} onRetry={refresh} />}

      {isLoading && (
        <div className={styles.bar}>
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} height={74} radius={16} />
          ))}
        </div>
      )}

      {status === 'ready' && !hasReferrals && (
        <EmptyState
          title="No referrals yet"
          description="Share your referral link with friends to start tracking your stats here."
          actionLabel="Copy Referral Link"
        />
      )}

      {status === 'ready' && hasReferrals && (
        <div className={styles.bar}>
          {stats.map((stat, i) => (
            <StatBar key={stat.id} stat={stat} index={i} />
          ))}
        </div>
      )}

      {status === 'ready' && (data?.spamReferrals ?? 0) > 0 && (
        <p className={styles.note}>
          Some referral attempts were not eligible for rewards.
        </p>
      )}
    </div>
  );
}

export default StatsSection;

import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useMotionValue, useTransform, animate } from 'framer-motion';
import { Users, CheckCircle2, Clock, Coins, Zap, Gem, Eye, EyeOff } from 'lucide-react';
import { statistics } from '../../utils/dummyData';
import FloatingOrbs from '../common/FloatingOrbs';
import FloatingRewardIcons from '../common/FloatingRewardIcons';
import EmptyState from '../common/EmptyState';
import CoinScatterBackground from '../common/CoinScatterBackground';
import styles from './StatsSection.module.css';

const ICONS = {
  total: Users,
  success: CheckCircle2,
  pending: Clock,
  earnings: Coins,
  xp: Zap,
  gems: Gem,
};

const ACCENTS = {
  total: 'indigo',
  success: 'emerald',
  pending: 'amber',
  earnings: 'gold',
  xp: 'teal',
  gems: 'rose',
};

function Counter({ value }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-40px' });
  const motionVal = useMotionValue(0);
  const rounded = useTransform(motionVal, (latest) => Math.round(latest).toLocaleString('en-IN'));
  const [display, setDisplay] = useState('0');

  useEffect(() => {
    if (!isInView) return;
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
  const [showEmpty, setShowEmpty] = useState(false);

  return (
    <div className={styles.panel}>
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
        <p className={styles.subtitle}>Track every milestone of your referral journey</p>

        <button className={styles.demoToggle} onClick={() => setShowEmpty((v) => !v)}>
          {showEmpty ? <Eye size={14} /> : <EyeOff size={14} />}
          {showEmpty ? 'Show sample data' : 'Preview empty state'}
        </button>
      </motion.div>

      {showEmpty ? (
        <EmptyState
          title="No referrals yet"
          description="Share your referral link with friends to start tracking your stats here."
          actionLabel="Copy Referral Link"
        />
      ) : (
        <div className={styles.bar}>
          {statistics.map((stat, i) => (
            <StatBar key={stat.id} stat={stat} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

export default StatsSection;
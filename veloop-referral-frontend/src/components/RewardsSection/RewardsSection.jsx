import { useRef } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { Lock, CheckCircle2, Sparkles } from 'lucide-react';
import { useMilestones } from '../../hooks/useMilestones';
import FloatingOrbs from '../common/FloatingOrbs';
import Skeleton from '../common/Skeleton';
import styles from './RewardsSection.module.css';
import CoinScatterBackground from '../common/CoinScatterBackground';

function TiltCard({ reward, index }) {
  const ref = useRef(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springConfig = { stiffness: 150, damping: 18 };
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [10, -10]), springConfig);
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-10, 10]), springConfig);

  const handleMouseMove = (e) => {
    const rect = ref.current.getBoundingClientRect();
    x.set((e.clientX - rect.left) / rect.width - 0.5);
    y.set((e.clientY - rect.top) / rect.height - 0.5);
  };

  const unlocked = reward.unlocked;

  return (
    <motion.div
      ref={ref}
      className={`${styles.card} ${unlocked ? styles.unlocked : styles.locked}`}
      style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => {
        x.set(0);
        y.set(0);
      }}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
    >
      <div className={styles.cardInner} style={{ transform: 'translateZ(30px)' }}>
        <div className={styles.statusIcon}>
          {unlocked ? <CheckCircle2 size={18} /> : <Lock size={16} />}
        </div>
        <div className={styles.sparkleIcon}>
          <Sparkles size={26} />
        </div>
        <h3 className={styles.rewardTitle}>{reward.label}</h3>
        {reward.subtitle && <p className={styles.rewardSubtitle}>{reward.subtitle}</p>}
        <p className={styles.condition}>{reward.condition}</p>
        {reward.credited && <div className={styles.unlockedBadge}>Credited</div>}
        {!reward.credited && unlocked && <div className={styles.unlockedBadge}>Unlocked</div>}
      </div>
      <div className={styles.shine} />
    </motion.div>
  );
}

/** Milestone definitions + unlock state come from the backend config table. */
function RewardsSection() {
  const { milestones, loading: isLoading } = useMilestones();

  return (
    <div className={styles.panel} id="rewards">
      <CoinScatterBackground />
      <FloatingOrbs />

      <motion.div
        className={styles.header}
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
      >
        <h2 className={styles.title}>Referral Rewards</h2>
        <p className={styles.subtitle}>Unlock exciting rewards as your friends complete tasks</p>
      </motion.div>

      <div className={styles.grid}>
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={190} radius={18} />)
          : milestones.map((reward, i) => <TiltCard key={reward.id} reward={reward} index={i} />)}
      </div>
    </div>
  );
}

export default RewardsSection;

import { useRef } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { Lock, CheckCircle2, Sparkles } from 'lucide-react';
import { rewards, referralInfo } from '../../utils/dummyData';
import FloatingOrbs from '../common/FloatingOrbs';
import styles from './RewardsSection.module.css';
import CoinScatterBackground from '../common/CoinScatterBackground';

function TiltCard({ reward, index, unlocked }) {
  const ref = useRef(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const springConfig = { stiffness: 150, damping: 18 };
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [10, -10]), springConfig);
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-10, 10]), springConfig);

  const handleMouseMove = (e) => {
    const rect = ref.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    x.set(px);
    y.set(py);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      ref={ref}
      className={`${styles.card} ${unlocked ? styles.unlocked : styles.locked}`}
      style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
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

        <h3 className={styles.rewardTitle}>{reward.title}</h3>
        {reward.subtitle && <p className={styles.rewardSubtitle}>{reward.subtitle}</p>}

        <p className={styles.condition}>{reward.condition}</p>

        {unlocked && <div className={styles.unlockedBadge}>Unlocked</div>}
      </div>

      <div className={styles.shine} />
    </motion.div>
  );
}

function RewardsSection() {
  const current = referralInfo.totalReferrals;

  return (
    <div className={styles.panel}>
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
        {rewards.map((reward, i) => {
          const unlocked = reward.requiredTasks === 0 || current >= reward.requiredTasks;
          return <TiltCard key={reward.id} reward={reward} index={i} unlocked={unlocked} />;
        })}
      </div>
    </div>
  );
}

export default RewardsSection;
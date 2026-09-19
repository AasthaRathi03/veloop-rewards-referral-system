import { motion } from 'framer-motion';
import { UserPlus, Trophy } from 'lucide-react';
import { useReferral } from '../../context/ReferralContext';
import { useMilestones } from '../../hooks/useMilestones';
import FloatingOrbs from '../common/FloatingOrbs';
import CoinScatterBackground from '../common/CoinScatterBackground';
import Skeleton from '../common/Skeleton';
import styles from './RewardTimeline.module.css';

function RewardTimeline() {
  const { data } = useReferral();
  const { milestones: allMilestones, loading: isLoading } = useMilestones();
  const milestones = allMilestones.filter((m) => m.milestone > 0);

  const steps = [
    {
      id: 'start',
      title: 'Registration',
      desc: 'Your friend registers through your referral link (+20 XP)',
      achieved: (data?.totalReferrals ?? 0) > 0,
      isStart: true,
    },
    ...milestones.map((m) => ({
      id: m.id,
      title: m.label,
      desc: m.condition,
      achieved: m.unlocked,
    })),
  ];

  const achievedRatio = steps.filter((s) => s.achieved).length / Math.max(steps.length, 1);

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
        <h2 className={styles.title}>Your Reward Journey</h2>
        <p className={styles.subtitle}>Every verified ad brings you closer to the next reward</p>
      </motion.div>

      {isLoading ? (
        <Skeleton height={260} radius={18} />
      ) : (
        <div className={styles.timeline}>
          <div className={styles.trackBg} />
          <motion.div
            className={styles.trackFill}
            initial={{ scaleY: 0 }}
            animate={{ scaleY: achievedRatio }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            style={{ transformOrigin: 'top' }}
          />

          {steps.map((step, i) => (
            <motion.div
              key={step.id}
              className={styles.step}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.5, delay: i * 0.12 }}
            >
              <div className={`${styles.node} ${step.achieved ? styles.nodeAchieved : ''}`}>
                {step.isStart ? <UserPlus size={16} /> : <Trophy size={16} />}
              </div>
              <div className={styles.content}>
                <h4 className={styles.stepTitle}>{step.title}</h4>
                <p className={styles.stepDesc}>{step.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RewardTimeline;

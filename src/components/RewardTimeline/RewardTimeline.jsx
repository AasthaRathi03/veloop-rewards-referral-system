import { motion } from 'framer-motion';
import { UserPlus, Trophy } from 'lucide-react';
import { rewards, referralInfo } from '../../utils/dummyData';
import FloatingOrbs from '../common/FloatingOrbs';
import CoinScatterBackground from '../common/CoinScatterBackground';
import styles from './RewardTimeline.module.css';

function RewardTimeline() {
  const current = referralInfo.totalReferrals;

  const milestoneRewards = rewards.filter((r) => r.requiredTasks > 0);

  const steps = [
    { id: 'start', title: 'Registration', desc: 'You joined the referral program', achieved: true, isStart: true },
    ...milestoneRewards.map((r) => ({
      id: r.id,
      title: r.title,
      desc: r.condition,
      achieved: current >= r.requiredTasks,
    })),
  ];

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
        <p className={styles.subtitle}>Every referral brings you closer to the next reward</p>
      </motion.div>

      <div className={styles.timeline}>
        <div className={styles.trackBg} />
        <motion.div
          className={styles.trackFill}
          initial={{ scaleY: 0 }}
          whileInView={{
            scaleY: steps.filter((s) => s.achieved).length / steps.length,
          }}
          viewport={{ once: true, margin: '-100px' }}
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
    </div>
  );
}

export default RewardTimeline;
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check } from 'lucide-react';
import { useReferral } from '../../context/ReferralContext';
import ConfettiBurst from '../common/ConfettiBurst';
import Toast from '../common/Toast';
import Skeleton from '../common/Skeleton';
import styles from './ReferralCard.module.css';

function ReferralCard() {
  const { data, isLoading } = useReferral();
  const [copiedField, setCopiedField] = useState(null);
  const [burstId, setBurstId] = useState(0);
  const [toast, setToast] = useState({ show: false, message: '' });

  // Referral code + link are ALWAYS backend values.
  const code = data?.referralCode ?? '';
  const link = data?.referralLink ?? '';

  const handleCopy = async (text, field, label) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setBurstId((id) => id + 1);
      setToast({ show: true, message: `${label} copied!` });
      setTimeout(() => setCopiedField(null), 2000);
      setTimeout(() => setToast({ show: false, message: '' }), 2200);
    } catch (err) {
      console.error('Copy failed', err);
    }
  };

  return (
    <motion.div
      className={styles.card}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.3 }}
    >
      <div className={styles.row}>
        <div className={styles.field}>
          <span className={styles.label}>Your Referral Code</span>
          {isLoading ? (
            <Skeleton width={160} height={26} />
          ) : (
            <span className={styles.value}>{code || '—'}</span>
          )}
        </div>
        <div className={styles.copyBtnWrap}>
          <ConfettiBurst burstId={copiedField === 'code' ? burstId : 0} />
          <button
            className={styles.copyBtn}
            onClick={() => handleCopy(code, 'code', 'Referral code')}
            disabled={!code}
            aria-label="Copy referral code"
          >
            {copiedField === 'code' ? <Check size={18} /> : <Copy size={18} />}
            {copiedField === 'code' ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      <div className={styles.divider} />

      <div className={styles.row}>
        <div className={styles.field}>
          <span className={styles.label}>Referral Link</span>
          {isLoading ? (
            <Skeleton width={230} height={18} />
          ) : (
            <span className={styles.valueSmall}>{link || '—'}</span>
          )}
        </div>
        <div className={styles.copyBtnWrap}>
          <ConfettiBurst burstId={copiedField === 'link' ? burstId : 0} />
          <button
            className={styles.copyBtn}
            onClick={() => handleCopy(link, 'link', 'Referral link')}
            disabled={!link}
            aria-label="Copy referral link"
          >
            {copiedField === 'link' ? <Check size={18} /> : <Copy size={18} />}
            {copiedField === 'link' ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      <Toast show={toast.show} message={toast.message} />
    </motion.div>
  );
}

export default ReferralCard;

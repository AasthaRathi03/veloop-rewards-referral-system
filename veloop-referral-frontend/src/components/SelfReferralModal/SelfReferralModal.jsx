import { AnimatePresence, motion } from 'framer-motion';
import { ShieldAlert, X } from 'lucide-react';
import styles from './SelfReferralModal.module.css';

/**
 * Shown when the backend returns SELF_REFERRAL_DETECTED / DEVICE_ALREADY_ASSOCIATED.
 * The masked email is provided by the backend - the client never unmasks anything.
 */
function SelfReferralModal({ open, maskedEmail, message, onClose, onLogin }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={styles.overlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          role="presentation"
        >
          <motion.div
            className={styles.modal}
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 260, damping: 22 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="self-referral-title"
          >
            <button className={styles.close} onClick={onClose} aria-label="Close">
              <X size={18} />
            </button>

            <div className={styles.iconWrap}>
              <ShieldAlert size={26} />
            </div>

            <h3 id="self-referral-title" className={styles.title}>
              Account Already Exists
            </h3>
            <p className={styles.body}>
              {message ||
                'This device has already been associated with a VELOOP Rewards account. Please use your existing account to continue.'}
            </p>

            {maskedEmail && (
              <div className={styles.accountBox}>
                <span className={styles.accountLabel}>Account</span>
                <span className={styles.accountValue}>{maskedEmail}</span>
              </div>
            )}

            <div className={styles.actions}>
              <button className={styles.primary} onClick={onLogin}>
                Login
              </button>
              <button className={styles.secondary} onClick={onClose}>
                Close
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default SelfReferralModal;

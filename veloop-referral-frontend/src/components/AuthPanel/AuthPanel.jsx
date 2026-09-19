import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { LogIn, UserPlus } from 'lucide-react';
import { login, register } from '../../api/referrals';
import { useReferral } from '../../context/ReferralContext';
import SelfReferralModal from '../SelfReferralModal/SelfReferralModal';
import styles from './AuthPanel.module.css';

/**
 * Minimal auth surface so the referral page can be demonstrated end to end.
 * In production this is replaced by VELOOP's existing auth flow - only the
 * access token + device headers matter to this page.
 */
function AuthPanel() {
  const { onAuthChange } = useReferral();
  const [mode, setMode] = useState('register');
  const [form, setForm] = useState({ email: '', password: '', phone: '', referralCode: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState({ open: false, maskedEmail: null, message: '' });

  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get('ref');
    if (ref) setForm((f) => ({ ...f, referralCode: ref.toUpperCase() }));
  }, []);

  const update = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === 'login') {
        await login(form.email.trim(), form.password);
      } else {
        await register({
          email: form.email.trim(),
          password: form.password,
          phone: form.phone.trim() || undefined,
          referralCode: form.referralCode.trim() || undefined,
        });
      }
      onAuthChange();
    } catch (err) {
      if (err.code === 'SELF_REFERRAL_DETECTED' || err.code === 'DEVICE_ALREADY_ASSOCIATED') {
        setModal({ open: true, maskedEmail: err.maskedEmail, message: err.message });
      } else if (err.code === 'VALIDATION_ERROR' && err.details?.length) {
        setError(err.details.map((d) => `${d.field}: ${d.issue}`).join(' | '));
      } else {
        setError(err.message);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      className={styles.panel}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className={styles.tabs}>
        <button
          type="button"
          className={mode === 'register' ? styles.tabActive : styles.tab}
          onClick={() => setMode('register')}
        >
          <UserPlus size={15} /> Create account
        </button>
        <button
          type="button"
          className={mode === 'login' ? styles.tabActive : styles.tab}
          onClick={() => setMode('login')}
        >
          <LogIn size={15} /> Login
        </button>
      </div>

      <p className={styles.hint}>
        Sign in to see your referral code, stats and rewards. Every value on this page is served by
        the VELOOP backend.
      </p>

      <form className={styles.form} onSubmit={submit}>
        <label className={styles.field}>
          <span>Email</span>
          <input type="email" required value={form.email} onChange={update('email')} autoComplete="email" />
        </label>

        <label className={styles.field}>
          <span>Password</span>
          <input
            type="password"
            required
            minLength={8}
            value={form.password}
            onChange={update('password')}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          />
        </label>

        {mode === 'register' && (
          <>
            <label className={styles.field}>
              <span>Phone (optional)</span>
              <input type="tel" value={form.phone} onChange={update('phone')} placeholder="+919876543210" />
            </label>
            <label className={styles.field}>
              <span>Referral code (optional)</span>
              <input
                type="text"
                value={form.referralCode}
                onChange={update('referralCode')}
                placeholder="VELOOPABC12"
              />
            </label>
          </>
        )}

        {error && <p className={styles.error}>{error}</p>}

        <button type="submit" className={styles.submit} disabled={busy}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Login' : 'Create account'}
        </button>
      </form>

      <SelfReferralModal
        open={modal.open}
        maskedEmail={modal.maskedEmail}
        message={modal.message}
        onClose={() => setModal({ open: false, maskedEmail: null, message: '' })}
        onLogin={() => {
          setModal({ open: false, maskedEmail: null, message: '' });
          setMode('login');
        }}
      />
    </motion.div>
  );
}

export default AuthPanel;

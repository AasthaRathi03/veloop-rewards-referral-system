import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getReferralDashboard, getSpamReferrals, trackReferralClick } from '../api/referrals';
import { getToken } from '../api/client';

const ReferralContext = createContext(null);

export function ReferralProvider({ children }) {
  const [data, setData] = useState(null);
  const [spam, setSpam] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | loading | ready | error | unauthenticated
  const [error, setError] = useState(null);
  const [authVersion, setAuthVersion] = useState(0);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setStatus('unauthenticated');
      setData(null);
      return;
    }
    setStatus((prev) => (prev === 'ready' ? 'ready' : 'loading'));
    try {
      const [dashboard, spamData] = await Promise.all([getReferralDashboard(), getSpamReferrals()]);
      setData(dashboard);
      setSpam(spamData);
      setStatus('ready');
      setError(null);
    } catch (err) {
      if (err.code === 'UNAUTHORIZED') {
        setStatus('unauthenticated');
        setData(null);
        return;
      }
      setError(err);
      setStatus('error');
    }
  }, []);

  // A ?ref= landing is recorded as a CLICK only - never as a referral.
  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get('ref');
    if (ref) trackReferralClick(ref).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh, authVersion]);

  const value = useMemo(
    () => ({
      data,
      spam,
      status,
      error,
      refresh,
      onAuthChange: () => setAuthVersion((v) => v + 1),
      isLoading: status === 'loading' || status === 'idle',
    }),
    [data, spam, status, error, refresh],
  );

  return <ReferralContext.Provider value={value}>{children}</ReferralContext.Provider>;
}

export function useReferral() {
  const ctx = useContext(ReferralContext);
  if (!ctx) throw new Error('useReferral must be used inside <ReferralProvider>');
  return ctx;
}

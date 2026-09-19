import { useEffect, useState } from 'react';
import { getMilestoneConfig } from '../api/referrals';
import { useReferral } from '../context/ReferralContext';

/**
 * Milestone definitions always come from the backend.
 * Signed in  -> personalised list (unlocked/credited flags) from /referrals/me
 * Signed out -> public program config from /referrals/config/milestones
 */
export function useMilestones() {
  const { data, status } = useReferral();
  const [fallback, setFallback] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    if (data?.rewardMilestones?.length) {
      setLoading(false);
      return () => {
        active = false;
      };
    }
    if (status === 'loading' || status === 'idle') return () => {};
    getMilestoneConfig()
      .then((res) => {
        if (active) setFallback(res.milestones ?? []);
      })
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [data, status]);

  return {
    milestones: data?.rewardMilestones?.length ? data.rewardMilestones : fallback,
    loading: loading && !(data?.rewardMilestones?.length),
  };
}

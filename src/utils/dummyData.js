// ============================================
// Dummy data for VELoop Referral Page
// (Backend integration not required per task spec)
// ============================================

export const referralInfo = {
  code: '18642076',
  link: 'velooprewards.vercel.app/register?ref=18642076',
  totalReferrals: 18,
  earnings: 35000,
  earningsUnit: 'SVE',
  pendingRewards: 4,
};

export const statistics = [
  { id: 'total', label: 'Total Referrals', value: 18 },
  { id: 'success', label: 'Successful Referrals', value: 14 },
  { id: 'pending', label: 'Pending Referrals', value: 4 },
  { id: 'earnings', label: 'Total Rewards Earned', value: 35000, unit: 'SVE' },
  { id: 'xp', label: 'Total XP Earned', value: 280 },
  { id: 'gems', label: 'Total Gems Earned', value: 40 },
];

export const rewards = [
  {
    id: 'r1',
    title: '5000 SVE',
    subtitle: '≈ ₹10',
    condition: 'Friend completes 15 Ad Watch tasks',
    requiredTasks: 15,
  },
  {
    id: 'r2',
    title: '2 Lucky Spins',
    subtitle: null,
    condition: 'Friend completes 20 Ad Watch tasks',
    requiredTasks: 20,
  },
  {
    id: 'r3',
    title: '5000 Tokens',
    subtitle: null,
    condition: 'Friend completes 30 Ad Watch tasks',
    requiredTasks: 30,
  },
  {
    id: 'r4',
    title: '10 Gems',
    subtitle: null,
    condition: 'Friend completes 35 Ad Watch tasks',
    requiredTasks: 35,
  },
  {
    id: 'r5',
    title: '+20 XP',
    subtitle: null,
    condition: 'Awarded for every successful referral',
    requiredTasks: 0,
  },
];

export const referralRules = [
  'Rewards are unlocked only after the referred user completes the required number of Ad Watch tasks.',
  'Each referral reward is milestone-based and can only be claimed after the respective condition is met.',
  'Multiple successful referrals can unlock multiple rewards.',
  'Self-referrals are not allowed.',
  'Fraudulent or fake referrals will result in reward cancellation.',
  'Referral progress should be tracked clearly through the UI.',
];

export const faqData = [
  {
    id: 'faq1',
    question: 'How do I earn rewards from referrals?',
    answer:
      'Share your referral code or link with friends. Once they sign up and complete the required Ad Watch tasks, you unlock the corresponding milestone rewards.',
  },
  {
    id: 'faq2',
    question: 'When do I receive my reward?',
    answer:
      'Rewards are credited automatically once your referred friend completes the task threshold for that milestone.',
  },
  {
    id: 'faq3',
    question: 'Is there a limit to how many friends I can refer?',
    answer:
      'No limit. Every successful referral earns you XP, and each one can unlock multiple milestone rewards.',
  },
];

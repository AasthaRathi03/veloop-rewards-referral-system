// ============================================================
// STATIC PAGE COPY ONLY.
//
// All user-specific values (referral code, link, stats, balances, milestones,
// ad progress, spam counts) now come from the backend via /api/referrals/me.
// Nothing user-specific may be added to this file again.
// ============================================================

export const referralRules = [
  'Rewards are unlocked only after the referred user completes the required number of verified Ad Watch tasks.',
  'Each referral reward is milestone-based and is credited automatically once the condition is met.',
  'Every milestone is credited exactly once per referral.',
  'Self-referrals and multi-account abuse are detected and receive no rewards.',
  'A referred account can only ever have one referrer.',
  'Referral progress and balances are maintained by the VELOOP backend.',
];

export const faqData = [
  {
    id: 'faq1',
    question: 'How do I earn rewards from referrals?',
    answer:
      'Share your referral code or link with friends. Once they sign up and complete the required Ad Watch tasks, the backend verifies each ad completion and credits the corresponding milestone rewards.',
  },
  {
    id: 'faq2',
    question: 'When do I receive my reward?',
    answer:
      'Rewards are credited automatically once your referred friend crosses a milestone. Each credit is recorded in your reward ledger, so support can always trace it.',
  },
  {
    id: 'faq3',
    question: 'Is there a limit to how many friends I can refer?',
    answer:
      'No limit. Every successful referral earns you XP, and each referred friend can unlock the full milestone set.',
  },
  {
    id: 'faq4',
    question: 'Why is one of my referrals marked as spam?',
    answer:
      'Some referral attempts are not eligible, for example when the same device creates multiple accounts. Those referrals do not earn rewards.',
  },
];

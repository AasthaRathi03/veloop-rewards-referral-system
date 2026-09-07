# VELoop Rewards — Referral Page Redesign

A complete UI/UX redesign of the VELoop Rewards Referral Page, built as part of the Frontend Internship Program (Task 01). The goal was to reimagine the referral experience with a modern, premium, fintech-inspired interface — inspired by products like Cred, CoinDCX, and Stripe — while preserving all existing referral functionality.

**Live Demo:** [veloop-referral-redesign.vercel.app](https://veloop-referral-redesign.vercel.app)

---

## Features

- **Animated Hero Section** with gradient typography and subtle floating reward icons
- **Referral Card** with one-click copy for referral code and link, complete with confetti burst and toast feedback
- **Share Buttons** for WhatsApp, Instagram, Facebook, Copy Link, and Native Share (Web Share API with fallback)
- **Animated Statistics Bar** with count-up number animations
- **Referral Progress Tracker** showing milestone progress with an animated fill bar
- **3D Tilt Reward Cards** with locked/unlocked states based on referral progress
- **Reward Timeline** visualizing the full referral journey from registration to milestone rewards
- **Referral Rules** presented as an icon-based grid
- **FAQ Accordion** with smooth expand/collapse animations
- **Empty State UI** demonstrating the no-data experience
- **Fully Responsive** across mobile, tablet, laptop, and ultra-wide screens
- **Touch-optimized interactions** for mobile (tap feedback on all interactive elements)

## Tech Stacks

- **React.js** (Vite)
- **Bootstrap 5** (grid utilities)
- **CSS Modules** (component-scoped styling)
- **React Icons** & **Lucide React** (iconography)
- **Framer Motion** (animations and scroll-triggered effects)

## Folder Structure

```
src/
├── components/
│   ├── Hero/
│   ├── ReferralCard/
│   ├── ShareButtons/
│   ├── StatsSection/
│   ├── ReferralProgress/
│   ├── RewardsSection/
│   ├── RewardTimeline/
│   ├── ReferralRules/
│   ├── FAQ/
│   ├── Header/
│   ├── Footer/
│   └── common/          # Reusable: FloatingOrbs, EmptyState, Toast, ConfettiBurst
├── pages/
│   └── ReferralPage.jsx
├── hooks/
│   └── useWebShare.js
├── utils/
│   └── dummyData.js
└── styles/
    ├── variables.css     # Design tokens (colors, spacing, typography)
    └── global.css
```

## Installation & Setup

# Clone the repository
git clone https://github.com/Abhi0abhi0/veloop-referral-redesign.git

# Navigate into the project
cd veloop-referral-redesign

# Install dependencies
npm install

# Start the development server
npm run dev


The app will be available at `http://localhost:5173`

## Build for Production


npm run build


## Author

**Abhishek Tomar**
Frontend Development Intern — VELoop Rewards

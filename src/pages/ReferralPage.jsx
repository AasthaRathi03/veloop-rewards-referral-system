import styles from './ReferralPage.module.css';
import Header from '../components/Header/Header';
import Hero from '../components/Hero/Hero';
import ReferralCard from '../components/ReferralCard/ReferralCard';
import ShareButtons from '../components/ShareButtons/ShareButtons';
import StatsSection from '../components/StatsSection/StatsSection';
import ReferralProgress from '../components/ReferralProgress/ReferralProgress';
import RewardsSection from '../components/RewardsSection/RewardsSection';
import RewardTimeline from '../components/RewardTimeline/RewardTimeline';
import ReferralRules from '../components/ReferralRules/ReferralRules';
import FAQ from '../components/FAQ/FAQ';
import Footer from '../components/Footer/Footer';

function ReferralPage() {
  return (
    <div className={styles.page}>
      <Header />

      {/* ---------- DARK ZONE ---------- */}
      <section className={styles.darkZone}>
        <div className={styles.meshOverlay} aria-hidden="true" />
        <div className="container">
          <Hero />
          <ReferralCard />
          <ShareButtons />
        </div>
      </section>

      {/* ---------- LOWER ZONE ---------- */}
      <section className={styles.lightZone}>
        <div className="container">
          <StatsSection />
          <ReferralProgress />
          <RewardsSection />
          <RewardTimeline />
          <ReferralRules />
          <FAQ />
        </div>
      </section>

      <Footer />
    </div>
  );
}

export default ReferralPage;
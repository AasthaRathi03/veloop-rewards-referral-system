import styles from './ReferralPage.module.css';
import Header from '../components/Header/Header';
import Hero from '../components/Hero/Hero';
import ReferralCard from '../components/ReferralCard/ReferralCard';
import ShareButtons from '../components/ShareButtons/ShareButtons';
import StatsSection from '../components/StatsSection/StatsSection';
import ReferralProgress from '../components/ReferralProgress/ReferralProgress';
import ReferralList from '../components/ReferralList/ReferralList';
import RewardsSection from '../components/RewardsSection/RewardsSection';
import RewardTimeline from '../components/RewardTimeline/RewardTimeline';
import ReferralRules from '../components/ReferralRules/ReferralRules';
import AuthPanel from '../components/AuthPanel/AuthPanel';
import FAQ from '../components/FAQ/FAQ';
import Footer from '../components/Footer/Footer';
import { useReferral } from '../context/ReferralContext';

function ReferralPage() {
  const { status } = useReferral();
  const signedIn = status !== 'unauthenticated';

  return (
    <div className={styles.page}>
      <Header />

      {/* ---------- DARK ZONE ---------- */}
      <section className={styles.darkZone}>
        <div className={styles.meshOverlay} aria-hidden="true" />
        <div className="container">
          <Hero />
          {signedIn ? (
            <>
              <ReferralCard />
              <ShareButtons />
            </>
          ) : (
            <AuthPanel />
          )}
        </div>
      </section>

      {/* ---------- LOWER ZONE ---------- */}
      <section className={styles.lightZone}>
        <div className="container">
          {signedIn && (
            <>
              <StatsSection />
              <ReferralProgress />
              <ReferralList />
            </>
          )}
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

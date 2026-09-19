import { ReferralProvider } from './context/ReferralContext';
import ReferralPage from './pages/ReferralPage';

function App() {
  return (
    <ReferralProvider>
      <ReferralPage />
    </ReferralProvider>
  );
}

export default App;

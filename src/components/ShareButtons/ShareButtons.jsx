import { useState } from 'react';
import { motion } from 'framer-motion';
import { FaWhatsapp, FaInstagram, FaFacebookF } from 'react-icons/fa';
import { Link2, Share2, Check } from 'lucide-react';
import { referralInfo } from '../../utils/dummyData';
import { useWebShare } from '../../hooks/useWebShare';
import styles from './ShareButtons.module.css';

const shareUrl = 'https://' + referralInfo.link;
const shareText =
  'Join VELoop Rewards using my referral code ' +
  referralInfo.code +
  ' and start earning today!';
const whatsappMessage = shareText + ' ' + shareUrl;

function ShareButtons() {
  const [linkCopied, setLinkCopied] = useState(false);
  const { share, isSupported } = useWebShare();

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    } catch (err) {
      console.error('Copy failed', err);
    }
  };

  const handleNativeShare = async () => {
    const result = await share({
      title: 'VELoop Rewards',
      text: shareText,
      url: shareUrl,
    });
    if (result.unsupported) {
      handleCopyLink();
    }
  };

  const buttons = [
    {
      id: 'whatsapp',
      label: 'WhatsApp',
      icon: <FaWhatsapp size={20} />,
      href: 'https://wa.me/?text=' + encodeURIComponent(whatsappMessage),
      colorClass: styles.whatsapp,
    },
    {
      id: 'instagram',
      label: 'Instagram',
      icon: <FaInstagram size={20} />,
      href: 'https://instagram.com',
      colorClass: styles.instagram,
    },
    {
      id: 'facebook',
      label: 'Facebook',
      icon: <FaFacebookF size={20} />,
      href: 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(shareUrl),
      colorClass: styles.facebook,
    },
  ];

  return (
    <motion.div
      className={styles.wrapper}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.4 }}
    >
      <span className={styles.label}>Share via</span>

      <div className={styles.buttonRow}>
        {buttons.map((btn) => (
          <a
            key={btn.id}
            href={btn.href}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.iconBtn + ' ' + btn.colorClass}
            aria-label={'Share via ' + btn.label}
          >
            {btn.icon}
          </a>
        ))}

        <button
          className={styles.iconBtn + ' ' + styles.copyLink}
          onClick={handleCopyLink}
          aria-label="Copy referral link"
        >
          {linkCopied ? <Check size={20} /> : <Link2 size={20} />}
        </button>

        {isSupported && (
          <button
            className={styles.iconBtn + ' ' + styles.nativeShare}
            onClick={handleNativeShare}
            aria-label="More share options"
          >
            <Share2 size={20} />
          </button>
        )}
      </div>
    </motion.div>
  );
}

export default ShareButtons;

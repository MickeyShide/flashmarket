import React, { useState, useEffect } from 'react';

export const Countdown = ({ targetDate, onExpire }) => {
  const [timeLeft, setTimeLeft] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0, expired: false });
  const hasExpiredRef = React.useRef(false);

  useEffect(() => {
    hasExpiredRef.current = false;
    let interval = null;

    function calculate() {
      if (!targetDate) {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0, expired: true });
        return;
      }

      const targetTime = new Date(targetDate).getTime();
      const now = new Date().getTime();
      const diff = targetTime - now;

      if (diff <= 0) {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0, expired: true });
        if (interval) clearInterval(interval);
        if (!hasExpiredRef.current) {
          hasExpiredRef.current = true;
          if (onExpire) onExpire();
        }
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setTimeLeft({ days, hours, minutes, seconds, expired: false });
    }

    calculate();
    interval = setInterval(calculate, 1000);
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [targetDate, onExpire]);

  if (timeLeft.expired) {
    return <span className="font-mono text-red-500 font-extrabold">ЗАВЕРШЕН / СТАРТОВАЛ</span>;
  }

  const pad = (num) => String(num).padStart(2, '0');

  return (
    <div className="inline-flex items-center gap-1 font-mono text-xs font-black tracking-wider bg-black text-white px-2.5 py-1 rounded">
      {timeLeft.days > 0 && <span>{timeLeft.days}д </span>}
      <span>{pad(timeLeft.hours)}:{pad(timeLeft.minutes)}:{pad(timeLeft.seconds)}</span>
    </div>
  );
};

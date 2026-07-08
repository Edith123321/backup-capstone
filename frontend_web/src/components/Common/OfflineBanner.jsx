// frontend_web/src/components/Common/OfflineBanner.jsx
/**
 * Scenario 4 — Infrastructure Failure (Offline).
 *
 * A persistent, non-blocking banner that tells the nurse the truth about their
 * connection and their data: when Wi-Fi/3G drops mid-screening, recordings and
 * triage surveys are queued locally (IndexedDB/localStorage via offlineQueue)
 * and this banner reassures them that nothing is lost — "💾 Saved locally,
 * prediction pending" — so they can move to the next patient without fear.
 */
import React from 'react';
import { useOfflineSync } from '../../hooks/useOfflineSync';

const OfflineBanner = () => {
  const { isOffline, hasPending, pendingCount, isProcessing, triggerSync } = useOfflineSync();

  // Nothing to say when we're online and the queue is empty.
  if (!isOffline && !hasPending) return null;

  const barStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    padding: '8px 16px',
    fontSize: '0.88rem',
    fontWeight: 600,
    color: isOffline ? '#92400e' : '#1e3a8a',
    background: isOffline ? '#fef3c7' : '#dbeafe',
    borderBottom: `1px solid ${isOffline ? '#f59e0b' : '#3b82f6'}`,
  };

  return (
    <div style={barStyle} role="status" aria-live="polite">
      <span>
        {isOffline
          ? `📴 You are offline. ${pendingCount || 0} item(s) saved locally — predictions pending (waiting for internet).`
          : isProcessing
            ? `🔄 Back online — syncing ${pendingCount || 0} saved item(s)…`
            : `💾 ${pendingCount || 0} item(s) saved locally, prediction pending.`}
      </span>
      {!isOffline && hasPending && !isProcessing && (
        <button
          onClick={triggerSync}
          style={{
            border: 'none', background: '#2563eb', color: '#fff',
            padding: '4px 12px', borderRadius: 6, cursor: 'pointer', fontWeight: 600,
          }}
        >
          Sync now
        </button>
      )}
    </div>
  );
};

export default OfflineBanner;

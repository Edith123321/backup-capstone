// frontend_web/src/hooks/useOfflineSync.js
import { useState, useEffect, useCallback } from 'react';
import offlineQueue, { syncStatus, syncQueue } from '../services/offlineQueue';

export const useOfflineSync = () => {
  const [status, setStatus] = useState(syncStatus());
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Update status
  const updateStatus = useCallback(() => {
    setStatus(syncStatus());
  }, []);

  // Handle sync progress
  const handleProgress = useCallback((progressValue, msg) => {
    setProgress(progressValue);
    setMessage(msg);
    updateStatus();
  }, [updateStatus]);

  // Handle sync complete
  const handleSyncComplete = useCallback(() => {
    setIsProcessing(false);
    updateStatus();
  }, [updateStatus]);

  // Handle sync success
  const handleSyncSuccess = useCallback(() => {
    updateStatus();
  }, [updateStatus]);

  // Handle sync error
  const handleSyncError = useCallback(() => {
    updateStatus();
  }, [updateStatus]);

  // Set up listeners
  useEffect(() => {
    offlineQueue.onSyncProgress(handleProgress);
    offlineQueue.onSyncSuccess(handleSyncSuccess);
    offlineQueue.onSyncError(handleSyncError);
    
    // Listen for custom event
    window.addEventListener('offline_sync_complete', handleSyncComplete);
    
    // Update status periodically
    const interval = setInterval(updateStatus, 10000);
    
    return () => {
      window.removeEventListener('offline_sync_complete', handleSyncComplete);
      clearInterval(interval);
    };
  }, [handleProgress, handleSyncComplete, handleSyncSuccess, handleSyncError, updateStatus]);

  // Trigger sync
  const triggerSync = useCallback(async () => {
    if (status.isProcessing || !status.isOnline) {
      return;
    }
    
    setIsProcessing(true);
    try {
      await syncQueue();
    } catch (error) {
      console.error('Sync error:', error);
    } finally {
      setIsProcessing(false);
      updateStatus();
    }
  }, [status, updateStatus]);

  // Check if offline
  const isOffline = !status.isOnline;
  const hasPending = status.hasPendingItems || status.hasFailedItems;
  const pendingCount = status.pendingCount || status.pending;

  return {
    status,
    progress,
    message,
    isProcessing,
    isOffline,
    hasPending,
    pendingCount,
    triggerSync,
    updateStatus,
    queueItems: () => offlineQueue.getQueueItems(),
    clearQueue: (statusFilter) => offlineQueue.clearQueue(statusFilter),
    retryItem: (id) => offlineQueue.retryItem(id)
  };
};

export default useOfflineSync;
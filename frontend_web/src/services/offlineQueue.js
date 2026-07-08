// frontend_web/src/services/offlineQueue.js
/**
 * Offline Queue Manager for RHD Detection System
 * Handles offline data storage and synchronization
 * Implements the "Gisozi" Test - Offline Resilience
 */

// Native UUID generator — avoids an external dependency and works offline.
// Falls back to a timestamp-random id on very old browsers.
const uuidv4 = () =>
  (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function')
    ? globalThis.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

// ============================================
// CONSTANTS
// ============================================

const STORAGE_KEYS = {
  QUEUE: 'offline_queue',
  PENDING: 'offline_pending_count',
  SYNC_STATUS: 'offline_sync_status',
  CACHED_DATA: 'offline_cached_data',
  LAST_SYNC: 'offline_last_sync'
};

const MAX_RETRY_ATTEMPTS = 5;
const RETRY_DELAY_MS = 5000; // 5 seconds
const MAX_QUEUE_SIZE = 1000;
const MAX_CACHE_SIZE_MB = 50;

// ============================================
// OFFLINE QUEUE CLASS
// ============================================

class OfflineQueueManager {
  constructor() {
    this.queue = [];
    this.isProcessing = false;
    this.isOnline = navigator.onLine;
    this.syncCallbacks = [];
    this.errorCallbacks = [];
    this.progressCallbacks = [];
    this.lastSyncTime = null;
    this.pendingCount = 0;
    
    // Initialize queue from storage
    this._loadQueue();
    
    // Set up online/offline listeners
    this._setupListeners();
    
    // Initialize sync status
    this._updateSyncStatus();
    
    console.log('📱 Offline Queue Manager initialized');
    console.log(`📊 Queue contains ${this.queue.length} pending items`);
  }

  // ============================================
  // PUBLIC METHODS
  // ============================================

  /**
   * Add a request to the offline queue
   * @param {Object} request - Request object {method, url, data, headers, params}
   * @param {Object} options - Additional options {priority, retryCount, id}
   * @returns {Promise} - Resolves with queued item ID
   */
  async enqueue(request, options = {}) {
    const id = options.id || uuidv4();
    
    const queueItem = {
      id,
      method: request.method || 'GET',
      url: request.url,
      data: request.data || null,
      headers: request.headers || {},
      params: request.params || {},
      timestamp: new Date().toISOString(),
      priority: options.priority || 'normal', // 'high', 'normal', 'low'
      retryCount: options.retryCount || 0,
      maxRetries: options.maxRetries || MAX_RETRY_ATTEMPTS,
      status: 'pending', // 'pending', 'processing', 'completed', 'failed'
      error: null,
      createdAt: new Date().toISOString()
    };

    // Check queue size limit
    if (this.queue.length >= MAX_QUEUE_SIZE) {
      // Remove oldest low-priority items
      const lowPriorityItems = this.queue
        .filter(item => item.priority === 'low')
        .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
      
      if (lowPriorityItems.length > 0) {
        this.queue = this.queue.filter(item => item.id !== lowPriorityItems[0].id);
        console.warn(`⚠️ Queue size limit reached. Removed oldest low-priority item.`);
      } else {
        throw new Error('Queue is full. Please sync before adding more items.');
      }
    }

    // Add to queue
    this.queue.push(queueItem);
    this._saveQueue();
    this._updatePendingCount();
    this._updateSyncStatus();

    console.log(`📥 Added to queue: ${queueItem.method} ${queueItem.url} (ID: ${queueItem.id})`);

    // If online, process immediately
    if (this.isOnline && !this.isProcessing) {
      this.processQueue();
    }

    return { id, status: 'queued', message: 'Request queued for offline sync' };
  }

  /**
   * Process the offline queue
   * @returns {Promise} - Resolves when processing complete
   */
  async processQueue() {
    if (this.isProcessing) {
      console.log('⏳ Queue processing already in progress');
      return;
    }

    if (!this.isOnline) {
      console.log('📴 Offline - Cannot process queue');
      return;
    }

    const pendingItems = this.queue.filter(item => item.status === 'pending');
    if (pendingItems.length === 0) {
      console.log('✅ No pending items to process');
      return;
    }

    this.isProcessing = true;
    console.log(`🔄 Processing ${pendingItems.length} queue items...`);

    let completed = 0;
    let failed = 0;
    let total = pendingItems.length;

    // Sort by priority
    const priorityOrder = { high: 0, normal: 1, low: 2 };
    const sortedItems = pendingItems.sort((a, b) => {
      return (priorityOrder[a.priority] || 1) - (priorityOrder[b.priority] || 1);
    });

    for (const item of sortedItems) {
      try {
        const progress = ((completed + failed) / total) * 100;
        this._notifyProgress(progress, `Syncing ${item.method} ${item.url}`);
        
        item.status = 'processing';
        this._saveQueue();
        
        const response = await this._executeRequest(item);
        
        // Request successful
        item.status = 'completed';
        item.completedAt = new Date().toISOString();
        this._saveQueue();
        
        completed++;
        console.log(`✅ Synced: ${item.method} ${item.url} (${completed}/${total})`);
        
        // Notify success
        this._notifySyncSuccess(item, response);
        
        // Update RHD status based on response if applicable
        if (response && response.success) {
          await this._handleSuccessfulSync(item, response);
        }
        
      } catch (error) {
        // Request failed
        item.status = 'failed';
        item.error = error.message || 'Unknown error';
        item.retryCount += 1;
        this._saveQueue();
        
        failed++;
        console.error(`❌ Failed to sync: ${item.method} ${item.url}`, error);
        
        // Notify error
        this._notifyError(item, error);
        
        // If retry limit reached, keep in queue but mark as failed
        if (item.retryCount >= item.maxRetries) {
          console.warn(`⚠️ Max retries reached for ${item.id}`);
        }
      }
      
      // Update progress
      this._updatePendingCount();
      this._updateSyncStatus();
    }

    // Remove completed items from queue
    this.queue = this.queue.filter(item => 
      item.status !== 'completed' || item.retryCount >= item.maxRetries
    );
    this._saveQueue();
    this._updatePendingCount();
    this._updateSyncStatus();

    this.isProcessing = false;
    
    console.log(`✅ Queue processing complete. Completed: ${completed}, Failed: ${failed}`);
    this._notifyProgress(100, 'Sync complete');
    
    // Notify completion
    this._notifySyncComplete(completed, failed);
    
    // Schedule retry for failed items
    const failedItems = this.queue.filter(item => 
      item.status === 'failed' && item.retryCount < item.maxRetries
    );
    
    if (failedItems.length > 0) {
      console.log(`⏰ Scheduling retry for ${failedItems.length} failed items in ${RETRY_DELAY_MS}ms`);
      setTimeout(() => this.processQueue(), RETRY_DELAY_MS);
    }
  }

  /**
   * Get queue status
   * @returns {Object} - Queue status information
   */
  getStatus() {
    const pending = this.queue.filter(item => item.status === 'pending').length;
    const processing = this.queue.filter(item => item.status === 'processing').length;
    const failed = this.queue.filter(item => item.status === 'failed').length;
    const completed = this.queue.filter(item => item.status === 'completed').length;
    
    return {
      isOnline: this.isOnline,
      isProcessing: this.isProcessing,
      totalItems: this.queue.length,
      pending,
      processing,
      failed,
      completed,
      lastSyncTime: this.lastSyncTime,
      pendingCount: this.pendingCount,
      queueSize: this.queue.length,
      hasFailedItems: failed > 0,
      hasPendingItems: pending > 0,
      canSync: this.isOnline && !this.isProcessing && (pending > 0 || failed > 0)
    };
  }

  /**
   * Clear the offline queue
   * @param {string} status - Optional status to clear ('failed', 'completed', 'pending')
   */
  clearQueue(status = null) {
    if (status) {
      this.queue = this.queue.filter(item => item.status !== status);
    } else {
      this.queue = [];
    }
    this._saveQueue();
    this._updatePendingCount();
    this._updateSyncStatus();
    console.log('🗑️ Queue cleared');
  }

  /**
   * Get all queue items
   * @param {string} status - Optional status filter
   * @returns {Array} - Queue items
   */
  getQueueItems(status = null) {
    if (status) {
      return this.queue.filter(item => item.status === status);
    }
    return this.queue;
  }

  /**
   * Remove specific item from queue
   * @param {string} id - Item ID
   */
  removeItem(id) {
    this.queue = this.queue.filter(item => item.id !== id);
    this._saveQueue();
    this._updatePendingCount();
    this._updateSyncStatus();
  }

  /**
   * Retry a specific failed item
   * @param {string} id - Item ID
   */
  retryItem(id) {
    const item = this.queue.find(i => i.id === id);
    if (item && item.status === 'failed') {
      item.status = 'pending';
      item.retryCount = 0;
      this._saveQueue();
      this._updatePendingCount();
      
      if (this.isOnline) {
        this.processQueue();
      }
    }
  }

  // ============================================
  // EVENT CALLBACKS
  // ============================================

  /**
   * Register a callback for sync success events
   * @param {Function} callback - Callback function
   */
  onSyncSuccess(callback) {
    if (typeof callback === 'function') {
      this.syncCallbacks.push(callback);
    }
  }

  /**
   * Register a callback for sync error events
   * @param {Function} callback - Callback function
   */
  onSyncError(callback) {
    if (typeof callback === 'function') {
      this.errorCallbacks.push(callback);
    }
  }

  /**
   * Register a callback for sync progress events
   * @param {Function} callback - Callback function
   */
  onSyncProgress(callback) {
    if (typeof callback === 'function') {
      this.progressCallbacks.push(callback);
    }
  }

  // ============================================
  // PRIVATE METHODS
  // ============================================

  /**
   * Execute a queued request
   * @param {Object} item - Queue item
   * @returns {Promise} - Response from API
   */
  async _executeRequest(item) {
    const { method, url, data, headers, params } = item;
    
    // Build URL with params
    let fullUrl = url;
    if (params && Object.keys(params).length > 0) {
      const urlParams = new URLSearchParams(params);
      fullUrl = `${url}?${urlParams.toString()}`;
    }
    
    // Get token from localStorage
    const token = localStorage.getItem('token');
    
    // Prepare headers
    const requestHeaders = {
      'Content-Type': 'application/json',
      ...headers
    };
    
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }
    
    // Prepare request options
    const options = {
      method: method,
      headers: requestHeaders
    };
    
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(data);
    }
    
    // Execute fetch
    const response = await fetch(fullUrl, options);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  }

  /**
   * Handle successful sync
   * @param {Object} item - Queue item
   * @param {Object} response - API response
   */
  async _handleSuccessfulSync(item, response) {
    // If it's a prediction result, update patient RHD status
    if (item.url.includes('/screening/predict') || item.url.includes('/database/recordings')) {
      try {
        const { patient_id, prediction, confidence } = response;
        if (patient_id && prediction) {
          // Update patient RHD status if prediction is RHD
          if (prediction === 'RHD') {
            await this._updatePatientRHDStatus(patient_id, prediction, confidence);
          }
        }
      } catch (error) {
        console.error('Error updating RHD status after sync:', error);
      }
    }
  }

  /**
   * Update patient RHD status
   * @param {string} patientId - Patient ID
   * @param {string} prediction - Prediction result
   * @param {number} confidence - Confidence score
   */
  async _updatePatientRHDStatus(patientId, prediction, confidence) {
    try {
      // Import database API
      const { databaseApi } = await import('./api');
      
      const status = prediction === 'RHD' ? 'suspected' : 'none';
      
      await databaseApi.updatePatientRHDStatus(patientId, {
        rhd_status: status,
        rhd_notes: `Updated from offline sync. Confidence: ${(confidence * 100).toFixed(1)}%`,
        last_rhd_assessment: new Date().toISOString()
      });
      
      console.log(`✅ Updated RHD status for patient ${patientId}: ${status}`);
    } catch (error) {
      console.error('Error updating RHD status:', error);
    }
  }

  /**
   * Set up online/offline event listeners
   */
  _setupListeners() {
    window.addEventListener('online', () => {
      console.log('🌐 Connection restored - Processing queue...');
      this.isOnline = true;
      this._updateSyncStatus();
      
      // Process queue when online
      if (!this.isProcessing) {
        this.processQueue();
      }
    });
    
    window.addEventListener('offline', () => {
      console.log('📴 Connection lost - Going offline');
      this.isOnline = false;
      this._updateSyncStatus();
    });
  }

  /**
   * Load queue from localStorage
   */
  _loadQueue() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.QUEUE);
      if (stored) {
        this.queue = JSON.parse(stored);
        // Validate queue items
        this.queue = this.queue.filter(item => 
          item && typeof item === 'object' && item.id
        );
      }
    } catch (error) {
      console.error('Error loading queue:', error);
      this.queue = [];
    }
  }

  /**
   * Save queue to localStorage
   */
  _saveQueue() {
    try {
      localStorage.setItem(STORAGE_KEYS.QUEUE, JSON.stringify(this.queue));
    } catch (error) {
      console.error('Error saving queue:', error);
      
      // If storage is full, clear some space
      if (error.name === 'QuotaExceededError') {
        console.warn('⚠️ Storage quota exceeded. Cleaning up...');
        this._cleanupStorage();
        try {
          localStorage.setItem(STORAGE_KEYS.QUEUE, JSON.stringify(this.queue));
        } catch (retryError) {
          console.error('Failed to save queue after cleanup:', retryError);
        }
      }
    }
  }

  /**
   * Clean up storage when quota exceeded
   */
  _cleanupStorage() {
    // Remove oldest completed items
    const completedItems = this.queue
      .filter(item => item.status === 'completed')
      .sort((a, b) => new Date(a.completedAt) - new Date(b.completedAt));
    
    // Keep only last 10 completed items
    if (completedItems.length > 10) {
      const toRemove = completedItems.slice(0, completedItems.length - 10);
      this.queue = this.queue.filter(item => 
        !toRemove.some(remove => remove.id === item.id)
      );
      console.log(`🧹 Removed ${toRemove.length} old completed items`);
    }
  }

  /**
   * Update pending count
   */
  _updatePendingCount() {
    this.pendingCount = this.queue.filter(item => 
      item.status === 'pending' || item.status === 'processing'
    ).length;
    localStorage.setItem(STORAGE_KEYS.PENDING, this.pendingCount.toString());
  }

  /**
   * Update sync status
   */
  _updateSyncStatus() {
    const status = {
      isOnline: this.isOnline,
      isProcessing: this.isProcessing,
      pendingCount: this.pendingCount,
      lastSync: this.lastSyncTime
    };
    localStorage.setItem(STORAGE_KEYS.SYNC_STATUS, JSON.stringify(status));
  }

  /**
   * Notify sync success callbacks
   */
  _notifySyncSuccess(item, response) {
    this.syncCallbacks.forEach(callback => {
      try {
        callback(item, response);
      } catch (error) {
        console.error('Error in sync success callback:', error);
      }
    });
  }

  /**
   * Notify sync error callbacks
   */
  _notifyError(item, error) {
    this.errorCallbacks.forEach(callback => {
      try {
        callback(item, error);
      } catch (callbackError) {
        console.error('Error in sync error callback:', callbackError);
      }
    });
  }

  /**
   * Notify sync progress callbacks
   */
  _notifyProgress(progress, message) {
    this.progressCallbacks.forEach(callback => {
      try {
        callback(progress, message);
      } catch (error) {
        console.error('Error in sync progress callback:', error);
      }
    });
  }

  /**
   * Notify sync completion
   */
  _notifySyncComplete(completed, failed) {
    this.lastSyncTime = new Date().toISOString();
    localStorage.setItem(STORAGE_KEYS.LAST_SYNC, this.lastSyncTime);
    
    // Dispatch custom event for UI components
    window.dispatchEvent(new CustomEvent('offline_sync_complete', {
      detail: { completed, failed, total: completed + failed }
    }));
  }
}

// ============================================
// SINGLETON INSTANCE
// ============================================

const offlineQueue = new OfflineQueueManager();

// ============================================
// EXPORTS
// ============================================

export const syncStatus = () => offlineQueue.getStatus();

export const syncQueue = () => offlineQueue.processQueue();

export const clearQueue = (status = null) => offlineQueue.clearQueue(status);

export const getQueueItems = (status = null) => offlineQueue.getQueueItems(status);

export const removeQueueItem = (id) => offlineQueue.removeItem(id);

export const retryQueueItem = (id) => offlineQueue.retryItem(id);

export const enqueueRequest = (request, options) => offlineQueue.enqueue(request, options);

export const onSyncSuccess = (callback) => offlineQueue.onSyncSuccess(callback);

export const onSyncError = (callback) => offlineQueue.onSyncError(callback);

export const onSyncProgress = (callback) => offlineQueue.onSyncProgress(callback);

// Export the singleton
export default offlineQueue;
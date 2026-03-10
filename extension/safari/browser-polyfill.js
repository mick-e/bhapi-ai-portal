/**
 * Bhapi AI Safety Monitor — Safari Browser API Polyfill
 *
 * Maps Safari's webkit namespace to the standard browser.* API used by
 * Manifest V3 extensions. This polyfill ensures the shared extension code
 * works across Chrome, Firefox, and Safari without modification.
 *
 * Safari supports most WebExtension APIs natively since Safari 15.4+,
 * but some edge cases require shimming.
 */

(function () {
  "use strict";

  // If browser.* is already defined (Firefox, or modern Safari), skip polyfill
  if (typeof globalThis.browser !== "undefined" && globalThis.browser.runtime) {
    return;
  }

  // If chrome.* is available (Safari 15.4+ exposes chrome namespace), alias it
  if (typeof globalThis.chrome !== "undefined" && globalThis.chrome.runtime) {
    globalThis.browser = globalThis.chrome;
    return;
  }

  // ---------------------------------------------------------------------------
  // Fallback polyfill for older Safari versions or edge cases
  // ---------------------------------------------------------------------------

  const browser = {};

  // ---- runtime ----
  browser.runtime = {
    /**
     * Send a message to the background service worker.
     * Wraps chrome.runtime.sendMessage with Promise support.
     */
    sendMessage: function (message) {
      return new Promise(function (resolve, reject) {
        if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
          chrome.runtime.sendMessage(message, function (response) {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(response);
            }
          });
        } else {
          reject(new Error("Safari runtime messaging not available"));
        }
      });
    },

    /**
     * Add a message listener.
     */
    onMessage: {
      addListener: function (callback) {
        if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
          chrome.runtime.onMessage.addListener(callback);
        }
      },
      removeListener: function (callback) {
        if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
          chrome.runtime.onMessage.removeListener(callback);
        }
      },
    },

    /**
     * Send a message to the native Safari extension handler.
     */
    sendNativeMessage: function (applicationId, message) {
      return new Promise(function (resolve, reject) {
        if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendNativeMessage) {
          chrome.runtime.sendNativeMessage(applicationId, message, function (response) {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve(response);
            }
          });
        } else {
          reject(new Error("Native messaging not available"));
        }
      });
    },

    /**
     * Get the extension's internal URL for a resource.
     */
    getURL: function (path) {
      if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.getURL) {
        return chrome.runtime.getURL(path);
      }
      // Fallback: return the path as-is
      return path;
    },

    get id() {
      if (typeof chrome !== "undefined" && chrome.runtime) {
        return chrome.runtime.id;
      }
      return undefined;
    },

    get lastError() {
      if (typeof chrome !== "undefined" && chrome.runtime) {
        return chrome.runtime.lastError;
      }
      return null;
    },
  };

  // ---- storage.local ----
  browser.storage = {
    local: {
      /**
       * Get items from local storage.
       * @param {string|string[]|null} keys - Keys to retrieve, or null for all.
       */
      get: function (keys) {
        return new Promise(function (resolve, reject) {
          if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
            chrome.storage.local.get(keys, function (result) {
              if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
              } else {
                resolve(result);
              }
            });
          } else {
            // Fallback to localStorage
            var result = {};
            var keyList = Array.isArray(keys) ? keys : keys ? [keys] : [];
            keyList.forEach(function (key) {
              var value = localStorage.getItem("bhapi_" + key);
              if (value !== null) {
                try {
                  result[key] = JSON.parse(value);
                } catch (e) {
                  result[key] = value;
                }
              }
            });
            resolve(result);
          }
        });
      },

      /**
       * Set items in local storage.
       * @param {Object} items - Key-value pairs to store.
       */
      set: function (items) {
        return new Promise(function (resolve, reject) {
          if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
            chrome.storage.local.set(items, function () {
              if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
              } else {
                resolve();
              }
            });
          } else {
            // Fallback to localStorage
            Object.keys(items).forEach(function (key) {
              localStorage.setItem("bhapi_" + key, JSON.stringify(items[key]));
            });
            resolve();
          }
        });
      },

      /**
       * Remove items from local storage.
       * @param {string|string[]} keys - Keys to remove.
       */
      remove: function (keys) {
        return new Promise(function (resolve, reject) {
          if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
            chrome.storage.local.remove(keys, function () {
              if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
              } else {
                resolve();
              }
            });
          } else {
            var keyList = Array.isArray(keys) ? keys : [keys];
            keyList.forEach(function (key) {
              localStorage.removeItem("bhapi_" + key);
            });
            resolve();
          }
        });
      },
    },
  };

  globalThis.browser = browser;
})();

package ai.bhapi.safety.native

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.provider.Settings
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

/**
 * Phase 4 Task 29 (P4-NAT1) — Android Digital Wellbeing / UsageStatsManager bridge.
 *
 * Exposes per-app foreground-time data from the last 24 hours to JS.
 * Requires the special [android.Manifest.permission.PACKAGE_USAGE_STATS]
 * which cannot be granted at install — the user must flip the toggle
 * in system Settings. Use [openUsageStatsSettings] to jump there.
 *
 * Paired with @bhapi/shared-native's `getDailyAppUsage()` TS wrapper.
 */
class DigitalWellbeingBridge(
    reactContext: ReactApplicationContext
) : ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "DigitalWellbeingBridge"

    @ReactMethod
    fun getDailyAppUsage(promise: Promise) {
        try {
            val usm = reactApplicationContext
                .getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val end = System.currentTimeMillis()
            val start = end - 24L * 60L * 60L * 1000L
            val stats = usm.queryUsageStats(
                UsageStatsManager.INTERVAL_DAILY,
                start,
                end
            )

            val result = Arguments.createArray()
            if (stats != null) {
                for (stat in stats) {
                    // Skip zero-usage entries to keep the payload small
                    if (stat.totalTimeInForeground <= 0L) continue
                    val map = Arguments.createMap()
                    map.putString("packageName", stat.packageName ?: "")
                    map.putDouble("totalTimeMs", stat.totalTimeInForeground.toDouble())
                    map.putDouble("lastTimeUsed", stat.lastTimeUsed.toDouble())
                    result.pushMap(map)
                }
            }
            promise.resolve(result)
        } catch (e: SecurityException) {
            promise.reject(
                "PERMISSION_DENIED",
                "PACKAGE_USAGE_STATS not granted. Direct user to Settings."
            )
        } catch (e: Exception) {
            promise.reject("USAGE_STATS_ERROR", e.message ?: "unknown error")
        }
    }

    @ReactMethod
    fun openUsageStatsSettings(promise: Promise) {
        try {
            val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            reactApplicationContext.startActivity(intent)
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("INTENT_FAILED", e.message ?: "unknown error")
        }
    }
}

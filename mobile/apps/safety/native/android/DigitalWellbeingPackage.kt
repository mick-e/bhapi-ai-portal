package ai.bhapi.safety.native

import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager

/**
 * React Native package registration for [DigitalWellbeingBridge].
 *
 * Register this in `MainApplication.kt` by adding a new entry to the
 * `getPackages()` list:
 *     add(DigitalWellbeingPackage())
 */
class DigitalWellbeingPackage : ReactPackage {

    override fun createNativeModules(
        reactContext: ReactApplicationContext
    ): List<NativeModule> = listOf(DigitalWellbeingBridge(reactContext))

    override fun createViewManagers(
        reactContext: ReactApplicationContext
    ): List<ViewManager<*, *>> = emptyList()
}

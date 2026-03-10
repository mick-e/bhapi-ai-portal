import SafariServices
import os.log

/// Swift bridge class for the Bhapi AI Safety Monitor Safari Web Extension.
///
/// Handles messages sent from the browser extension via
/// `browser.runtime.sendNativeMessage()`. This allows the web extension
/// to communicate with native macOS/iOS capabilities when needed.
class SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {

    private let logger = Logger(
        subsystem: Bundle.main.bundleIdentifier ?? "ai.bhapi.safari-extension",
        category: "SafariWebExtensionHandler"
    )

    func beginRequest(with context: NSExtensionContext) {
        let request = context.inputItems.first as? NSExtensionItem

        let profile: UUID?
        if #available(iOS 17.0, macOS 14.0, *) {
            profile = request?.userInfo?[SFExtensionProfileKey] as? UUID
        } else {
            profile = nil
        }

        let message: Any?
        if #available(iOS 15.0, macOS 11.0, *) {
            message = request?.userInfo?[SFExtensionMessageKey]
        } else {
            message = request?.userInfo?["message"]
        }

        logger.log("Received native message from extension (profile: \(profile?.uuidString ?? "default", privacy: .public))")

        let response = NSExtensionItem()

        guard let messageDictionary = message as? [String: Any],
              let messageType = messageDictionary["type"] as? String else {
            logger.warning("Received invalid message format from extension")
            response.userInfo = [SFExtensionMessageKey: ["status": "error", "message": "Invalid message format"]]
            context.completeRequest(returningItems: [response], completionHandler: nil)
            return
        }

        switch messageType {
        case "STATUS_CHECK":
            // Extension is checking if native messaging is available
            response.userInfo = [SFExtensionMessageKey: [
                "status": "ok",
                "platform": "safari",
                "version": Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "unknown"
            ]]

        case "GET_NATIVE_CAPABILITIES":
            // Report what native capabilities are available
            response.userInfo = [SFExtensionMessageKey: [
                "status": "ok",
                "capabilities": [
                    "nativeMessaging": true,
                    "notifications": true
                ]
            ]]

        default:
            logger.info("Unhandled message type: \(messageType, privacy: .public)")
            response.userInfo = [SFExtensionMessageKey: [
                "status": "ok",
                "message": "Message received but not handled",
                "type": messageType
            ]]
        }

        context.completeRequest(returningItems: [response], completionHandler: nil)
    }
}

// PermissionKitBridge.swift
//
// Phase 4 Task 28 (R-23) — iOS 26 PermissionKit integration.
//
// Wraps Apple's PermissionKit (iOS 26) for cross-app parental approval.
// React Native surface is in `@bhapi/shared-native` — this file exposes
// `requestParentApproval(reason, childAccountId)` as a promise.
//
// Availability: only compiled + registered on iOS 26+. On older iOS versions
// the bridge is absent from `NativeModules` and the TS wrapper returns
// `{ status: 'unsupported', reason: 'bridge_missing' }`.

import Foundation
import React

#if canImport(PermissionKit)
import PermissionKit
#endif

@objc(PermissionKitBridge)
class PermissionKitBridge: NSObject {

  // MARK: - requestParentApproval

  @objc(requestParentApproval:childAccountId:resolver:rejecter:)
  func requestParentApproval(
    _ reason: String,
    childAccountId: String,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    #if canImport(PermissionKit)
    if #available(iOS 26.0, *) {
      PermissionKit.requestApproval(
        reason: reason,
        childId: childAccountId
      ) { result in
        switch result {
        case .approved:
          resolve(["status": "approved"])
        case .denied:
          resolve(["status": "denied"])
        case .timeout:
          resolve(["status": "timeout"])
        @unknown default:
          resolve(["status": "unsupported", "reason": "unknown_result"])
        }
      }
      return
    }
    #endif
    // Framework unavailable or pre-iOS 26
    resolve(["status": "unsupported", "reason": "pre_ios26_or_framework_missing"])
  }

  // MARK: - React Native boilerplate

  @objc
  static func requiresMainQueueSetup() -> Bool { false }

  @objc
  static func moduleName() -> String! { "PermissionKitBridge" }
}

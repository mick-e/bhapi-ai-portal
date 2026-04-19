// PermissionKitBridge.m — React Native module export
//
// Exposes PermissionKitBridge to the JS side. Paired with
// PermissionKitBridge.swift.

#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(PermissionKitBridge, NSObject)

RCT_EXTERN_METHOD(requestParentApproval:(NSString *)reason
                  childAccountId:(NSString *)childAccountId
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end

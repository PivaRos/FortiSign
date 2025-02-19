// SSLPinningDylib.m
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#import <Security/Security.h>
#import <CommonCrypto/CommonDigest.h>

#pragma mark - SSL Pinning via Certificate Fingerprint (Base64)

// Helper function to compute SHA256 fingerprint from certificate data and return it as a base64 string.
static NSString *fingerprintForCertificate(SecCertificateRef certificate) {
    CFDataRef certData = SecCertificateCopyData(certificate);
    if (!certData) {
        return nil;
    }
    const UInt8 *data = CFDataGetBytePtr(certData);
    CFIndex length = CFDataGetLength(certData);
    
    unsigned char hash[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256(data, (CC_LONG)length, hash);
    CFRelease(certData);
    
    // Create an NSData object from the hash and encode it in base64.
    NSData *hashData = [NSData dataWithBytes:hash length:CC_SHA256_DIGEST_LENGTH];
    NSString *base64Fingerprint = [hashData base64EncodedStringWithOptions:0];
    
    return base64Fingerprint;
}

// Reads the expected fingerprint from a file in the main bundle.
static NSString *expectedFingerprintFromBundle() {
    NSString *filePath = [[NSBundle mainBundle] pathForResource:@"expected_fingerprint" ofType:@"txt"];
    if (!filePath) {
        NSLog(@"[SSLPinning] expected_fingerprint.txt not found in bundle.");
        return nil;
    }
    NSError *error = nil;
    NSString *fingerprint = [NSString stringWithContentsOfFile:filePath encoding:NSUTF8StringEncoding error:&error];
    if (error) {
        NSLog(@"[SSLPinning] Error reading expected fingerprint: %@", error);
        return nil;
    }
    // Trim any whitespace/newlines.
    return [fingerprint stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
}

// Validate the server trust by comparing the base64-encoded SHA256 fingerprint of the leaf certificate.
static BOOL validateServerTrustWithFingerprint(SecTrustRef serverTrust) {
    SecCertificateRef certificate = SecTrustGetCertificateAtIndex(serverTrust, 0);
    if (!certificate) {
        NSLog(@"[SSLPinning] No certificate found in server trust.");
        return NO;
    }
    
    NSString *serverFingerprint = fingerprintForCertificate(certificate);
    if (!serverFingerprint) {
        NSLog(@"[SSLPinning] Could not compute fingerprint for server certificate.");
        return NO;
    }
    
    NSString *expectedFingerprint = expectedFingerprintFromBundle();
    if (!expectedFingerprint) {
        NSLog(@"[SSLPinning] Expected fingerprint not available.");
        return NO;
    }
    
    if ([serverFingerprint isEqualToString:expectedFingerprint]) {
        NSLog(@"[SSLPinning] Certificate fingerprint matched: %@", serverFingerprint);
        return YES;
    }
    
    NSLog(@"[SSLPinning] Certificate fingerprint mismatch. Got: %@, Expected: %@", serverFingerprint, expectedFingerprint);
    return NO;
}

#pragma mark - Method Swizzling

// Swizzled implementation for URLSession:didReceiveChallenge:completionHandler:
static void swizzled_URLSessionDidReceiveChallenge(id self, SEL _cmd, NSURLSession *session, NSURLAuthenticationChallenge *challenge, void (^completionHandler)(NSURLSessionAuthChallengeDisposition, NSURLCredential * _Nullable)) {
    if ([challenge.protectionSpace.authenticationMethod isEqualToString:NSURLAuthenticationMethodServerTrust]) {
        SecTrustRef serverTrust = challenge.protectionSpace.serverTrust;
        if (validateServerTrustWithFingerprint(serverTrust)) {
            NSURLCredential *credential = [NSURLCredential credentialForTrust:serverTrust];
            completionHandler(NSURLSessionAuthChallengeUseCredential, credential);
            return;
        } else {
            completionHandler(NSURLSessionAuthChallengeCancelAuthenticationChallenge, nil);
            return;
        }
    }
    
    SEL originalSelector = @selector(swizzled_URLSession:didReceiveChallenge:completionHandler:);
    if ([self respondsToSelector:originalSelector]) {
        void (*originalImp)(id, SEL, NSURLSession *, NSURLAuthenticationChallenge *, void (^)(NSURLSessionAuthChallengeDisposition, NSURLCredential * _Nullable)) = (void *)class_getMethodImplementation([self class], originalSelector);
        if (originalImp) {
            originalImp(self, originalSelector, session, challenge, completionHandler);
            return;
        }
    }
    completionHandler(NSURLSessionAuthChallengeCancelAuthenticationChallenge, nil);
}

// Helper function to perform swizzling on a given class.
static void swizzleURLSessionChallengeMethod(Class class) {
    SEL originalSelector = @selector(URLSession:didReceiveChallenge:completionHandler:);
    SEL swizzledSelector = @selector(swizzled_URLSession:didReceiveChallenge:completionHandler:);
    
    Method originalMethod = class_getInstanceMethod(class, originalSelector);
    Method swizzledMethod = class_getInstanceMethod(class, swizzledSelector);
    
    if (!originalMethod) {
        BOOL didAdd = class_addMethod(class, originalSelector, (IMP)swizzled_URLSessionDidReceiveChallenge, "v@:@@@?");
        if (didAdd) {
            NSLog(@"[SSLPinning] Added SSL pinning challenge method to class %@", NSStringFromClass(class));
        }
    } else {
        method_exchangeImplementations(originalMethod, swizzledMethod);
        NSLog(@"[SSLPinning] Swizzled SSL challenge method for class %@", NSStringFromClass(class));
    }
}

#pragma mark - Category on NSObject for Swizzling

@interface NSObject (SSLPinningSwizzle)
@end

@implementation NSObject (SSLPinningSwizzle)

+ (void)load {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        Class class = [self class];
        if (class_getInstanceMethod(class, @selector(URLSession:didReceiveChallenge:completionHandler:))) {
            SEL swizzledSelector = @selector(swizzled_URLSession:didReceiveChallenge:completionHandler:);
            BOOL didAddMethod = class_addMethod(class, swizzledSelector, (IMP)swizzled_URLSessionDidReceiveChallenge, "v@:@@@?");
            if (didAddMethod) {
                swizzleURLSessionChallengeMethod(class);
            }
        }
    });
}

@end

// End of dynamic library implementation.

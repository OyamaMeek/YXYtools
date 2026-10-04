#
# Be sure to run `pod lib lint ZJSDK_Pods.podspec' to ensure this is a
# valid spec before submitting.
#
# Any lines starting with a # are optional, but their use is encouraged
# To learn more about a Podspec see https://guides.cocoapods.org/syntax/podspec.html
#

Pod::Spec.new do |s|
  s.name             = 'ZJSDK'
  s.version          = '2.6.3.7'
  s.summary          = 'ZJSDK广告'
# This description is used to generate tags and improve search results.
#   * Think: What does it do? Why did you write it? What is the focus?
#   * Try to keep it short, snappy and to the point.
#   * Write the description between the DESC delimiters below.
#   * Finally, don't worry about the indent, CocoaPods strips it!

  s.description      = <<-DESC
TODO: Add long description of the pod here.
                       DESC

  s.homepage         = 'https://github.com/hzzhongjian/ZJSDK.git'
  # s.screenshots     = 'www.example.com/screenshots_1', 'www.example.com/screenshots_2'
  s.license          = { :type => 'MIT', :file => 'LICENSE' }
  s.author           = { 'hzzhongjian' => 'opentwo@hzzhongjian.cn' }
  s.source           = { :git => 'https://github.com/hzzhongjian/ZJSDK.git', :tag => s.version.to_s }
  # s.social_media_url = 'https://twitter.com/<TWITTER_USERNAME>'
  s.ios.deployment_target = '11.0'
  s.platform     = :ios, "11.0"
  
  #依赖的系统frameworks
  s.frameworks = ['UIKit','Foundation','StoreKit','MobileCoreServices','WebKit','MediaPlayer','CoreML','CoreMedia','CoreLocation','AVFoundation','CoreTelephony','SystemConfiguration','AdSupport','CoreMotion','Accelerate','QuartzCore','Security','ImageIO','CFNetwork','CoreGraphics','SafariServices','AVKit','DeviceCheck','CoreImage','MapKit','JavaScriptCore','CoreText','AddressBook','CoreData','MessageUI','QuickLook','AudioToolBox','Photos','LocalAuthentication','AssetsLibrary','CoreFoundation','CoreVideo','NetworkExtension']
  s.weak_frameworks = ['AppTrackingTransparency','CoreHaptics']
  #依赖的系统静态库
  #z表示libz.tdb,后缀不需要,lib开头的省略lib
  s.libraries = 'resolv.9','c++','z','sqlite3','bz2','xml2','c++abi','sqlite3.0','iconv'
  s.pod_target_xcconfig = { 'VALID_ARCHS' => 'x86_64 armv7 arm64', 'DEFINES_MODULE' => 'YES', 'EXCLUDED_ARCHS[sdk=iphonesimulator*]' => 'i386,arm64' }
  s.xcconfig = { 'ENABLE_BITCODE' => 'NO', 'OTHER_LDFLAGS' =>'-ObjC'}
#  valid_archs = ['armv7', 'i386', 'x86_64', 'arm64']
#  s.pod_target_xcconfig = {
#    'EXCLUDED_ARCHS[sdk=iphonesimulator*]' => 'arm64'
#  }
#  s.user_target_xcconfig = { 'EXCLUDED_ARCHS[sdk=iphonesimulator*]' => 'arm64' }
  s.default_subspecs = ['ZJSDKModuleQiYun','ZJSDKModuleDSP']
  
    s.subspec 'ZJAdSDK' do |ss|
        ss.vendored_frameworks = ['ZJSDK/ZJAdSDK/*.framework','ZJSDK/ZJAdSDK/*.xcframework']
        ss.preserve_paths = ['ZJSDK/ZJAdSDK/*.framework','ZJSDK/ZJAdSDK/*.xcframework']
        ss.resource = ['ZJSDK/ZJAdSDK/*.bundle']
    end
  
    s.subspec 'ZJSDKModuleQiYun' do |ss|
      ss.vendored_libraries = 'ZJSDK/ZJSDKModuleQiYun/*.a'
      ss.dependency 'ZJSDK/ZJAdSDK'
      ss.vendored_frameworks  = 'ZJSDK/ZJSDKModuleQiYun/*.xcframework'
      ss.preserve_paths       = 'ZJSDK/ZJSDKModuleQiYun/*.xcframework'
    end

    s.subspec 'ZJSDKModuleDSP' do |ss|
      ss.vendored_libraries = 'ZJSDK/ZJSDKModuleDSP/*.a'
      ss.dependency 'ZJSDK/ZJAdSDK'
      ss.dependency 'DSPSDK', '1.0.4.6'
    end

 
end


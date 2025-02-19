#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import zipfile

# Check command-line arguments: now we require 7 arguments:
# 1: IPA_FILE
# 2: FRAMEWORK_PATH (e.g. SSLPinningDylib.framework)
# 3: CERTIFICATE (signing identity string)
# 4: ENTITLEMENTS (path to entitlements plist)
# 5: EXPECTED_FINGERPRINT (as produced by your dynamic library, in base64 or hex)
# 6: PROVISIONING_PROFILE (path to the .mobileprovision file)
if len(sys.argv) != 7:
    print("Usage: python ios_ssl_pinning.py <IPA_FILE> <FRAMEWORK_PATH> <CERTIFICATE> <ENTITLEMENTS> <EXPECTED_FINGERPRINT> <PROVISIONING_PROFILE>")
    sys.exit(1)

IPA_FILE = sys.argv[1]
DYLIB_PATH = sys.argv[2]
CERTIFICATE = sys.argv[3]
ENTITLEMENTS = sys.argv[4]
EXPECTED_FINGERPRINT = sys.argv[5].strip()
PROVISIONING_PROFILE = sys.argv[6].strip()

WORK_DIR = "ipa_work"
EXTRACTED_PAYLOAD = os.path.join(WORK_DIR, "Payload")
OUTPUT_IPA = "modified.ipa"
FINGERPRINT_FILENAME = "expected_fingerprint.txt"

def run_command(command):
    """Executes a shell command and exits if there is an error."""
    print(f"🔨 Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error running command: {command}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def extract_ipa(ipa_path, work_dir):
    """Extracts the IPA (a ZIP archive) to a working directory."""
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    
    print("📂 Extracting IPA...")
    with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
        zip_ref.extractall(work_dir)
    print("✅ IPA extracted successfully.")

def locate_app(extracted_payload):
    """Finds the .app directory inside the Payload folder."""
    if not os.path.exists(extracted_payload):
        print("❌ Payload directory not found!")
        sys.exit(1)
    
    apps = [d for d in os.listdir(extracted_payload) if d.endswith(".app")]
    if not apps:
        print("❌ No .app directory found inside Payload!")
        sys.exit(1)
    
    app_path = os.path.join(extracted_payload, apps[0])
    print(f"📦 Found app bundle: {app_path}")
    return app_path

def inject_framework(app_path, framework_path):
    """
    Copies the entire framework into MyApp.app/Frameworks/ 
    and then modifies the main Mach-O binary to load it at runtime.
    """
    # Create Frameworks directory if it doesn't exist
    frameworks_dir = os.path.join(app_path, "Frameworks")
    os.makedirs(frameworks_dir, exist_ok=True)
    
    # The framework folder (e.g. SSLPinningDylib.framework)
    framework_name = os.path.basename(framework_path)
    target_framework_path = os.path.join(frameworks_dir, framework_name)
    
    print(f"📥 Copying framework from {framework_path} to {target_framework_path}")
    shutil.copytree(framework_path, target_framework_path, dirs_exist_ok=True)
    
    # Identify the main executable.
    app_name = os.path.splitext(os.path.basename(app_path))[0]
    main_executable = os.path.join(app_path, app_name)
    if not os.path.exists(main_executable):
        for item in os.listdir(app_path):
            potential = os.path.join(app_path, item)
            if os.path.isfile(potential) and os.access(potential, os.X_OK):
                main_executable = potential
                break
    print(f"🔍 Main executable identified as: {main_executable}")

    # The framework's binary usually has the same name as the framework (without .framework)
    framework_binary_name = os.path.splitext(framework_name)[0]
    # Build the injection path, e.g.: @executable_path/Frameworks/SSLPinningDylib.framework/SSLPinningDylib
    injection_path = f"@executable_path/Frameworks/{framework_name}/{framework_binary_name}"
    
    # Use insert_dylib to modify the main executable
    insert_cmd = f"insert_dylib --inplace --all-yes '{injection_path}' {main_executable}"
    print("🔧 Injecting framework binary into the main executable...")
    run_command(insert_cmd)
    print("✅ Framework injection complete.")

def inject_fingerprint_file(app_path, fingerprint):
    """Creates a file in the app bundle containing the expected fingerprint."""
    target_path = os.path.join(app_path, FINGERPRINT_FILENAME)
    print(f"📝 Creating fingerprint file at {target_path}")
    with open(target_path, "w") as f:
        f.write(fingerprint)
    print("✅ Fingerprint file created.")

def embed_provisioning_profile(app_path, provisioning_profile_path):
    """Copies the provisioning profile into the app bundle as embedded.mobileprovision."""
    target_path = os.path.join(app_path, "embedded.mobileprovision")
    print(f"📥 Embedding provisioning profile from {provisioning_profile_path} to {target_path}")
    shutil.copy(provisioning_profile_path, target_path)
    print("✅ Provisioning profile embedded.")

def remove_old_codesign(app_path):
    """Recursively removes old _CodeSignature directories from the app bundle."""
    print("🧹 Removing old code signatures...")
    for root, dirs, files in os.walk(app_path):
        for d in dirs:
            if d == "_CodeSignature":
                full_path = os.path.join(root, d)
                print(f"Removing: {full_path}")
                shutil.rmtree(full_path)
    print("✅ Old code signatures removed.")

def remove_embedded_provisioning(app_path):
    """Removes any embedded provisioning profiles from nested frameworks."""
    print("🧹 Removing embedded provisioning profiles from frameworks...")
    frameworks_dir = os.path.join(app_path, "Frameworks")
    if os.path.exists(frameworks_dir):
        for root, dirs, files in os.walk(frameworks_dir):
            for f in files:
                if f.endswith(".mobileprovision"):
                    full_path = os.path.join(root, f)
                    print(f"Removing embedded provisioning profile: {full_path}")
                    os.remove(full_path)
    print("✅ Embedded provisioning profiles removed.")

def sign_app(app_path, certificate, entitlements):
    """Re-signs the app bundle (including nested code) with the provided certificate and entitlements."""
    print("🔑 Signing app bundle with deep signing...")
    remove_old_codesign(app_path)
    remove_embedded_provisioning(app_path)
    sign_cmd = f'codesign -f --deep -s "{certificate}" --entitlements "{entitlements}" "{app_path}"'
    run_command(sign_cmd)
    print("✅ App bundle signed.")

def repackage_ipa(work_dir, output_ipa):
    """Zips the Payload folder back into an IPA using the system's zip command."""
    print("📦 Repackaging IPA using system zip...")
    cwd = os.getcwd()
    os.chdir(work_dir)
    output_path = os.path.join(cwd, output_ipa)
    zip_command = f"zip -r '{output_path}' Payload"
    print(f"🔨 Running: {zip_command}")
    subprocess.run(zip_command, shell=True, check=True)
    os.chdir(cwd)
    print(f"✅ IPA repackaged as: {output_ipa}")

def cleanup(work_dir):
    """Removes the working directory."""
    print("🧹 Cleaning up working directory...")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
        print(f"   Removed: {work_dir}")

def main():
    """Main function to handle the IPA injection process."""
    # 1. Extract IPA
    extract_ipa(IPA_FILE, WORK_DIR)
    
    # 2. Locate the app bundle inside the Payload directory
    app_path = locate_app(EXTRACTED_PAYLOAD)
    
    # 3. Inject the framework (SSL pinning logic via method swizzling)
    inject_framework(app_path, DYLIB_PATH)
    
    # 4. Inject the expected fingerprint file into the app bundle
    inject_fingerprint_file(app_path, EXPECTED_FINGERPRINT)
    
    # 5. Embed the provisioning profile into the app bundle
    embed_provisioning_profile(app_path, PROVISIONING_PROFILE)
    
    # 6. Re-sign the app bundle (deep signing will sign nested code as well)
    sign_app(app_path, CERTIFICATE, ENTITLEMENTS)
    
    # 7. Repackage the IPA
    repackage_ipa(WORK_DIR, OUTPUT_IPA)
    
    # 8. Cleanup
    cleanup(WORK_DIR)
    
    print("🚀 IPA wrapping complete! The modified IPA is ready for distribution.")

if __name__ == "__main__":
    main()

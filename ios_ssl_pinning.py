#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import zipfile

# Check command-line arguments
if len(sys.argv) != 5:
    print("Usage: python ios_ssl_pinning.py <IPA_FILE> <DYLIB_PATH> <CERTIFICATE> <ENTITLEMENTS>")
    sys.exit(1)

IPA_FILE = sys.argv[1]
DYLIB_PATH = sys.argv[2]
CERTIFICATE = sys.argv[3]
ENTITLEMENTS = sys.argv[4]

WORK_DIR = "ipa_work"
EXTRACTED_PAYLOAD = os.path.join(WORK_DIR, "Payload")
OUTPUT_IPA = "modified.ipa"

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
    """Extracts the IPA (which is just a ZIP archive) to a working directory."""
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

def inject_dylib(app_path, dylib_path):
    """
    Copies the dylib into the app bundle and uses insert_dylib to modify the Mach-O binary
    so that your dynamic library is loaded at runtime.
    """
    dylib_name = os.path.basename(dylib_path)
    target_dylib_path = os.path.join(app_path, dylib_name)
    
    print(f"📥 Copying {dylib_path} to {target_dylib_path}")
    shutil.copy(dylib_path, target_dylib_path)
    
    # Determine the main executable.
    # In many cases, the executable has the same name as the app bundle (without the .app extension).
    app_name = os.path.splitext(os.path.basename(app_path))[0]
    main_executable = os.path.join(app_path, app_name)
    if not os.path.exists(main_executable):
        # As a fallback, look for an executable file in the bundle.
        for item in os.listdir(app_path):
            potential = os.path.join(app_path, item)
            if os.path.isfile(potential) and os.access(potential, os.X_OK):
                main_executable = potential
                break
    print(f"🔍 Main executable identified as: {main_executable}")

    # Use insert_dylib to modify the main executable so that it loads your dylib.
    # Make sure that insert_dylib is installed and available in your PATH.
    insert_cmd = (
        f"insert_dylib --inplace --all-yes '@executable_path/{dylib_name}' {main_executable}"
    )
    print("🔧 Injecting dynamic library into the binary...")
    run_command(insert_cmd)
    print("✅ Dynamic library injection complete.")

def sign_app(app_path, certificate, entitlements):
    """Re-signs the app bundle with the provided certificate and entitlements."""
    print("🔑 Signing app bundle...")
    sign_cmd = (
        f'codesign -f -s "{certificate}" --entitlements "{entitlements}" "{app_path}"'
    )
    run_command(sign_cmd)
    print("✅ App bundle signed.")

def repackage_ipa(work_dir, output_ipa):
    """Zips the Payload folder back into an IPA."""
    print("📦 Repackaging IPA...")
    # Change working directory so that the ZIP does not include the work_dir folder
    cwd = os.getcwd()
    os.chdir(work_dir)
    with zipfile.ZipFile(os.path.join(cwd, output_ipa), 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the working directory and add files
        for root, dirs, files in os.walk("."):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path)
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
    
    # 3. Inject your dynamic library (which implements certificate pinning logic)
    inject_dylib(app_path, DYLIB_PATH)
    
    # 4. Re-sign the app bundle (this signs the executable and its resources)
    sign_app(app_path, CERTIFICATE, ENTITLEMENTS)
    
    # 5. Repackage the IPA
    repackage_ipa(WORK_DIR, OUTPUT_IPA)
    
    # 6. Cleanup
    cleanup(WORK_DIR)
    
    print("🚀 IPA wrapping complete! The modified IPA is ready for distribution.")

if __name__ == "__main__":
    main()

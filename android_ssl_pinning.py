import os
import re
import subprocess
import xml.etree.ElementTree as ET
import sys
import shutil

if len(sys.argv) != 8:
    print("Usage: python android_ssl_pinning.py <APK_FILE> <KEYSTORE_PATH> <KEY_ALIAS> <KEYSTORE_PASSWORD> <KEY_PASSWORD> <PINNED_DOMAIN> <PINNED_CERT_SHA256>")
    sys.exit(1)

APKTOOL_PATH = "apktool"
APK_FILE = sys.argv[1]
KEYSTORE_PATH = sys.argv[2]
KEY_ALIAS = sys.argv[3]
KEY_PASSWORD = sys.argv[4]
KEYSTORE_PASSWORD = sys.argv[5]
PINNED_DOMAIN = sys.argv[6]
PINNED_CERT_SHA256 = sys.argv[7]

def run_command(command):
    """Executes a shell command and handles errors."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error running command: {command}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def decompile_apk(apk_file):
    """Decompiles the APK into Smali code."""
    print("📂 Decompiling APK...")
    run_command(f"{APKTOOL_PATH} d {apk_file} -o extracted_apk --no-res")
    print("✅ APK Decompiled Successfully!")


def convert_manifest():
    """Converts binary AndroidManifest.xml to readable XML if needed, then restores it before rebuilding."""
    manifest_path = "extracted_apk/AndroidManifest.xml"
    backup_path = "extracted_apk/AndroidManifest_backup.xml"

    if not os.path.exists(manifest_path):
        print("❌ AndroidManifest.xml not found!")
        sys.exit(1)

    # Backup the original binary manifest
    if not os.path.exists(backup_path):
        os.rename(manifest_path, backup_path)

    with open(backup_path, "rb") as f:
        header = f.read(2)

    if header != b'<?':  # Convert only if it's binary
        print("🔄 Converting binary AndroidManifest.xml to readable format...")
        run_command(f"androguard axml {backup_path} > {manifest_path}")

def restore_manifest():
    """Restores the original binary AndroidManifest.xml before rebuilding."""
    backup_path = "extracted_apk/AndroidManifest_backup.xml"
    manifest_path = "extracted_apk/AndroidManifest.xml"

    if os.path.exists(backup_path):
        print("🔄 Restoring AndroidManifest.xml to binary format...")
        os.replace(backup_path, manifest_path)

def get_package_name():
    """Extracts the package name from AndroidManifest.xml and converts it back to binary after extraction."""
    convert_manifest()
    manifest_path = "extracted_apk/AndroidManifest.xml"
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    package_name = root.attrib.get("package", None)

    if package_name:
        smali_package_name = "L" + package_name.replace(".", "/") + "/"
        print(f"📦 Detected Package Name: {package_name} → Smali: {smali_package_name}")
        restore_manifest()  # Convert it back to binary before rebuilding
        return smali_package_name
    else:
        print("❌ Could not detect package name!")
        exit(1)

def find_network_library(package_name):
    """Scans only the base package directory for network-related classes in the app package."""
    
    # Remove leading "L" and trailing "/"
    base_package = package_name[1:].rstrip("/")

    # Locate smali directories
    smali_dirs = [d for d in os.listdir("extracted_apk") if d.startswith("smali")]

    # Network library identifiers (covering more variations)
    network_libraries = {
        "okhttp": ["Lokhttp3/OkHttpClient$Builder;", "Lokhttp3/OkHttpClient;"],  # 🔥 Expanded to match both
        "https_url_connection": ["Ljavax/net/ssl/HttpsURLConnection;"],
        "retrofit": ["Lretrofit2/Retrofit$Builder;"]
    }
    
    found_packages = {}

    print("🔍 Scanning for network libraries...")

    for smali_dir in smali_dirs:
        smali_path = os.path.join("extracted_apk", smali_dir)

        for root, dirs, files in os.walk(smali_path):
            # ✅ Strictly limit search to `base_package` and its sub-packages
            if not root.startswith(os.path.join(smali_path, base_package.replace("/", os.sep))):
                continue  # Skip unrelated directories

            for file in files:
                if file.endswith(".smali"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    for library, identifiers in network_libraries.items():
                        for identifier in identifiers:
                            if identifier in content:
                                found_packages[library] = filepath
                                print(f"✅ Detected {library} in {filepath}")

    if not found_packages:
        print("❌ No network libraries found in your package.")
        exit(1)

    return found_packages

def inject_security_wrapper(package_name):
    """
    Injects a minimal SecurityWrapper smali class into the APK that implements
    simple SSL pinning via a CertificatePinner using the correct method signature.
    The package_name is expected in the format "com/example/fortisign_test_pinning/"
    (without a leading "L").
    """
    import os

    package_name_clean = package_name.rstrip("/")
    base_smali_dir = os.path.join("extracted_apk", "smali")
    package_path = os.path.join(base_smali_dir, *package_name_clean.split("/"))
    os.makedirs(package_path, exist_ok=True)

    # -------------------------------
    # Create minimal SecurityWrapper.smali file with updated getPinnedClient
    # -------------------------------
    security_wrapper_path = os.path.join(package_path, "SecurityWrapper.smali")
    if not os.path.exists(security_wrapper_path):
        smali_code_sw = f""".class public L{package_name_clean}/SecurityWrapper;
.super Ljava/lang/Object;

.method public constructor <init>()V
    .locals 0
    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static getPinnedClient()Lokhttp3/OkHttpClient;
    .locals 6
    # Build a CertificatePinner with the pinned domain and certificate SHA256.
    new-instance v0, Lokhttp3/CertificatePinner$Builder;
    invoke-direct {{v0}}, Lokhttp3/CertificatePinner$Builder;-><init>()V
    const-string v1, "{PINNED_DOMAIN}"
    # Create a single-element string array for the certificate pin.
    const/4 v2, 1
    new-array v3, v2, [Ljava/lang/String;
    const-string v2, "sha256/{PINNED_CERT_SHA256}"
    # Load the index 0 into v4.
    const/4 v4, 0
    aput-object v2, v3, v4
    invoke-virtual {{v0, v1, v3}}, Lokhttp3/CertificatePinner$Builder;->add(Ljava/lang/String;[Ljava/lang/String;)Lokhttp3/CertificatePinner$Builder;
    move-result-object v0
    invoke-virtual {{v0}}, Lokhttp3/CertificatePinner$Builder;->build()Lokhttp3/CertificatePinner;
    move-result-object v0
    # Build OkHttpClient using the CertificatePinner.
    new-instance v1, Lokhttp3/OkHttpClient$Builder;
    invoke-direct {{v1}}, Lokhttp3/OkHttpClient$Builder;-><init>()V
    invoke-virtual {{v1, v0}}, Lokhttp3/OkHttpClient$Builder;->certificatePinner(Lokhttp3/CertificatePinner;)Lokhttp3/OkHttpClient$Builder;
    move-result-object v1
    invoke-virtual {{v1}}, Lokhttp3/OkHttpClient$Builder;->build()Lokhttp3/OkHttpClient;
    move-result-object v1
    return-object v1
.end method
"""
        with open(security_wrapper_path, "w", encoding="utf-8") as f:
            f.write(smali_code_sw)
        print(f"✅  SecurityWrapper injected at {security_wrapper_path}")
    else:
        print(f"ℹ️  SecurityWrapper already exists at {security_wrapper_path}")

def inject_ssl_pinning(smali_file, network_library, package_name):
    """
    Injects SSL pinning logic for OkHttp into the specified smali file.
    
    It replaces every instantiation of OkHttpClient (new-instance + <init>)
    with a call to SecurityWrapper.getPinnedClient().
    
    The package_name should be provided as: "com/example/fortisign_test_pinning/"
    (without a leading "L").
    """
    # We only support okhttp in this injection.
    if network_library.lower() != "okhttp":
        print("❌ Only OkHttp injection is supported in this function.")
        return

    # Build the class reference in smali format.
    # Must start with "L" and end with ";".
    smali_package = f"L{package_name}SecurityWrapper;"

    # Define the injection snippet.
    # We use a placeholder __REG__ to be replaced by the actual register.
    injection_code = (
        "invoke-static {}, " + smali_package +
        "->getPinnedClient()Lokhttp3/OkHttpClient;\n" +
        "    move-result-object __REG__"
    )

    with open(smali_file, "r", encoding="utf-8") as f:
        content = f.read()

    modified_content = content  # default

    # Pattern to match a new-instance followed by its <init> call.
    # It matches registers that start with either "v" or "p", so that it catches
    # cases like "new-instance p0, Lokhttp3/OkHttpClient;" as well.
    pattern = (
        r"new-instance\s+([pv]\d+),\s+Lokhttp3/OkHttpClient;\s*\n\s*"
        r"invoke-direct\s+\{\1\},\s+Lokhttp3/OkHttpClient;-><init>\(\)V"
    )

    def replacement(match):
        reg = match.group(1)  # e.g., v0 or p0
        # Replace the placeholder __REG__ with the actual register.
        injected = injection_code.replace("__REG__", reg)
        return injected

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count > 0:
        modified_content = new_content
        print(f"✅ Replaced {count} OkHttpClient constructor call(s) with SSL pinning injection in {smali_file}")
    else:
        # Fallback: if no explicit constructor was found, inject after the .locals declaration.
        print(f"ℹ️  No explicit OkHttpClient constructor found in {smali_file}. Using fallback injection after .locals.")
        locals_match = re.search(r"\.locals (\d+)", content)
        if locals_match:
            current_locals = int(locals_match.group(1))
            new_locals = max(current_locals, 2)
            content = re.sub(r"\.locals \d+", f".locals {new_locals}", content)
        method_match = re.search(r"(\.method.*?)(\.locals \d+)", content, re.DOTALL)
        if method_match:
            method_start, locals_line = method_match.groups()
            # Fallback injection uses v0.
            fallback_injection = (
                "invoke-static {}, " + smali_package +
                "->getPinnedClient()Lokhttp3/OkHttpClient;\n" +
                "    move-result-object v0"
            )
            modified_content = content.replace(locals_line, locals_line + "\n" + fallback_injection)
        else:
            print(f"❌ No valid method found in {smali_file}")
            return

    with open(smali_file, "w", encoding="utf-8") as f:
        f.write(modified_content)

    print(f"✅ SSL Pinning injected into {smali_file}")

def rebuild_and_sign_apk():
    """Rebuilds the APK, aligns it, signs it, and cleans up intermediate files for Android 7.0+ (API 24+)."""
    
    print("🔄 Rebuilding APK...")
    run_command("apktool b extracted_apk -o unsigned.apk --api 30")

    print("🔧 Aligning APK...")
    run_command("zipalign -v 4 unsigned.apk aligned.apk")

    print("🔑 Signing APK with apksigner...")
    sign_command = (
        f'apksigner sign --ks "{KEYSTORE_PATH}" --ks-pass pass:{KEYSTORE_PASSWORD} '
        f'--key-pass pass:{KEY_PASSWORD} --out final_signed.apk aligned.apk'
    )
    run_command(sign_command)

    print("✅ APK Signed Successfully: final_signed.apk")

    # Verify the signed APK
    print("🔍 Verifying APK signature...")
    run_command("apksigner verify --verbose --print-certs final_signed.apk")

    print("🚀 Installation Ready: final_signed.apk")
    
    # Cleanup intermediate files and directories
    print("🧹 Cleaning up intermediate files...")
    
    intermediate_files = ["unsigned.apk", "aligned.apk"]
    for file in intermediate_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"   Removed: {file}")
    
    # Remove the extracted directory if it exists
    if os.path.exists("extracted_apk"):
        if os.path.isdir("extracted_apk"):
            shutil.rmtree("extracted_apk")
            print("   Removed directory: extracted_apk")
        else:
            os.remove("extracted_apk")
            print("   Removed file: extracted_apk")


def main():
    """Main function to handle the entire SSL pinning injection process."""
    decompile_apk(APK_FILE)
    package_name = get_package_name()
    network_libraries = find_network_library(package_name)

    if len(network_libraries) > 0:
        inject_security_wrapper(package_name)

    for library, smali_file in network_libraries.items():
        inject_ssl_pinning(smali_file, library, package_name)

    restore_manifest()
    rebuild_and_sign_apk()
    print("🚀 SSL Pinning Injection Complete! Secured APK Ready.")

if __name__ == "__main__":
    main()

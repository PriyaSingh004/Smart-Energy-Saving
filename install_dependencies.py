"""
Install Missing Dependencies
Checks and installs required packages for the Smart Home Automation System
"""

import subprocess
import sys
import importlib.util


def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    spec = importlib.util.find_spec(import_name)
    return spec is not None


def install_package(package_name):
    """Install a package using pip"""
    try:
        print(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✓ {package_name} installed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package_name}")
        return False


def main():
    """Main function to check and install dependencies"""
    print("=" * 60)
    print("Smart Home Automation System - Dependency Checker")
    print("=" * 60)
    print()
    
    # Required packages
    packages = {
        'opencv-python': 'cv2',
        'numpy': 'numpy',
        'pillow': 'PIL',
        'ultralytics': 'ultralytics',
        'mediapipe': 'mediapipe',
        'pyserial': 'serial',
        'scipy': 'scipy',
        'matplotlib': 'matplotlib',
    }
    
    # Optional packages
    optional_packages = {
        'ultralytics': ('ultralytics', 'YOLO detection (recommended)'),
        'mediapipe': ('mediapipe', 'Pose estimation (recommended)'),
    }
    
    missing_required = []
    missing_optional = []
    
    print("Checking required packages...")
    for package, import_name in packages.items():
        if package in optional_packages:
            continue  # Skip optional packages for now
        
        if check_package(package, import_name):
            print(f"✓ {package} is installed")
        else:
            print(f"✗ {package} is NOT installed")
            missing_required.append(package)
    
    print()
    print("Checking optional packages...")
    for package, (import_name, description) in optional_packages.items():
        if check_package(package, import_name):
            print(f"✓ {package} is installed ({description})")
        else:
            print(f"✗ {package} is NOT installed ({description})")
            missing_optional.append(package)
    
    print()
    print("=" * 60)
    
    # Install missing packages
    if missing_required or missing_optional:
        print("\nInstalling missing packages...")
        print("-" * 60)
        
        # Install required packages first
        for package in missing_required:
            install_package(package)
        
        # Install optional packages
        if missing_optional:
            print("\nOptional packages (recommended for better performance):")
            for package in missing_optional:
                install_package(package)
        
        print()
        print("=" * 60)
        print("Installation complete!")
        print("You may need to restart the application for changes to take effect.")
    else:
        print("\n✓ All packages are installed!")
        print("You're ready to run the Smart Home Automation System.")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation interrupted by user.")
        sys.exit(0)




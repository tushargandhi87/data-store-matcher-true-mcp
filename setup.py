"""Setup script to install dependencies and verify configuration."""
import subprocess
import sys
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")


def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    version = sys.version_info
    if version < (3, 10):
        print(f"❌ Python 3.10+ required. Found: {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install required packages."""
    print("\nInstalling dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def check_env_file():
    """Check if .env file exists."""
    print("\nChecking environment configuration...")
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚠️  .env file not found")
        print("   Creating from .env.example...")
        
        example_file = Path(".env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✓ Created .env file")
            print("\n⚠️  IMPORTANT: Edit .env and add your CLAUDE_API_KEY")
            return False
        else:
            print("❌ .env.example not found")
            return False
    
    with open(env_file) as f:
        content = f.read()
        if "your-claude-api-key-here" in content or "CLAUDE_API_KEY=" in content and not "CLAUDE_API_KEY=sk-" in content:
            print("⚠️  CLAUDE_API_KEY not configured in .env")
            print("   Please edit .env and add your API key")
            return False
    
    print("✓ Environment configuration found")
    return True


def check_data_files():
    """Check if required data files exist."""
    print("\nChecking data files...")
    
    acat_file = Path("mcp_server/data/ACAT_Data_Stores_Master.xlsx")
    if not acat_file.exists():
        print(f"⚠️  ACAT reference file not found: {acat_file}")
        print("   Please place your ACAT reference file in mcp_server/data/")
        return False
    print(f"✓ ACAT reference file found")
    
    user_file = Path("input/user_input.xlsx")
    if not user_file.exists():
        print(f"⚠️  User input file not found: {user_file}")
        print("   You can use test_user_input.xlsx or create your own")
        
        test_file = Path("input/test_user_input.xlsx")
        if test_file.exists():
            print("   Test file available: input/test_user_input.xlsx")
    else:
        print(f"✓ User input file found")
    
    return True


def check_directories():
    """Ensure all required directories exist."""
    print("\nChecking directories...")
    
    dirs = ["mcp_server/data", "input", "output"]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✓ All directories ready")
    return True


def main():
    """Main setup process."""
    print_header("ACAT DATASTORE MATCHER - SETUP")
    
    if not check_python_version():
        print("\n❌ Setup failed: Python version check")
        return False
    
    check_directories()
    
    if not install_dependencies():
        print("\n❌ Setup failed: Dependency installation")
        return False
    
    env_ok = check_env_file()
    data_ok = check_data_files()
    
    print_header("SETUP SUMMARY")
    
    if env_ok and data_ok:
        print("✓ Setup complete! You can now run the agent:")
        print("\n  cd python_agent")
        print("  python agent.py")
        print("\n" + "=" * 60)
        return True
    else:
        print("⚠️  Setup incomplete. Please address the following:")
        if not env_ok:
            print("  - Configure .env file with your CLAUDE_API_KEY")
        if not data_ok:
            print("  - Add required data files")
        print("\nRun this script again after fixing the issues.")
        print("\n" + "=" * 60)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

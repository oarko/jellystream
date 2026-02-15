# Installation Guide

## Automated Setup (Recommended)

The easiest way to set up JellyStream is using the automated setup script, which handles:
- Virtual environment creation
- System dependency detection (Debian/Ubuntu)
- Package installation
- Configuration file setup

### Quick Install

```bash
chmod +x setup.sh
./setup.sh
```

The script will:
1. ✅ Detect your operating system
2. ✅ Check Python version (3.11+ required)
3. ✅ Install `python3-venv` on Debian/Ubuntu if needed
4. ✅ Create a virtual environment
5. ✅ Install all dependencies
6. ✅ Create `.env` configuration file
7. ✅ Set up data directories
8. ✅ Optionally start the application

### Running After Installation

Use the quick start script:

```bash
./start.sh
```

Or manually:

```bash
source venv/bin/activate
python run.py
```

## Manual Setup

If you prefer to set up manually or the automated script doesn't work for your system:

### 1. Install System Dependencies

**Debian/Ubuntu/Kubuntu:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev
```

**Fedora/RHEL:**
```bash
sudo dnf install python3 python3-pip python3-devel
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
```

### 3. Activate Virtual Environment

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### 4. Upgrade pip

```bash
pip install --upgrade pip
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

### 6. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
nano .env  # or use your preferred editor
```

### 7. Create Data Directories

```bash
mkdir -p data/database data/commercials data/logos
```

### 8. Run Application

```bash
python run.py
```

## Troubleshooting

### PEP 668 Error (Debian/Ubuntu)

If you see an error like:
```
error: externally-managed-environment
```

This is because modern Debian-based systems prevent installing packages system-wide. Solutions:

1. **Use the setup script** (recommended):
   ```bash
   ./setup.sh
   ```

2. **Manual fix** - Install python3-venv:
   ```bash
   sudo apt install python3-venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Permission Denied on Scripts

Make scripts executable:
```bash
chmod +x setup.sh start.sh
```

### Python Version Too Old

Check your Python version:
```bash
python3 --version
```

If it's older than 3.11, you may need to install a newer version:

**Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
# Use python3.11 instead of python3
python3.11 -m venv venv
```

### Missing Development Headers

If you get compilation errors during pip install:

**Debian/Ubuntu:**
```bash
sudo apt install python3-dev build-essential
```

**Fedora:**
```bash
sudo dnf install python3-devel gcc
```

### Port Already in Use

If port 8000 is already in use, edit `.env`:
```env
PORT=8001
```

## Docker Alternative

If you prefer not to deal with Python environments, use Docker:

```bash
docker-compose up -d
```

See [docs/SETUP.md](docs/SETUP.md) for more Docker information.

## Verification

After installation, verify everything works:

1. **Check health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Visit API docs:**
   ```
   http://localhost:8000/docs
   ```

3. **Run tests** (if dev dependencies installed):
   ```bash
   pytest
   ```

## Next Steps

- Configure Jellyfin connection in `.env`
- Read the [Setup Guide](docs/SETUP.md)
- Check the [API Documentation](docs/API.md)
- Create your first stream!

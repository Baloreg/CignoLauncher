# 🎮 CignoLauncher

A custom Minecraft launcher built for educational purposes to manage and distribute the Cignopack modpack. This project demonstrates modern software development practices including GUI design, API integration, and automated updates.

![Version](https://img.shields.io/badge/version-1.0.1-blue)
![Minecraft](https://img.shields.io/badge/Minecraft-1.20.1-green)
![Forge](https://img.shields.io/badge/Forge-47.4.6-orange)
![Python](https://img.shields.io/badge/Python-3.8+-yellow)

## 📚 Educational Project

This launcher was developed as a **school project** to explore:
- Desktop application development with Python and Tkinter
- OAuth 2.0 authentication flow with Microsoft Azure
- Automated software distribution and updates
- File integrity verification using SHA-256
- Multi-threaded operations and async programming
- Modern UI/UX design principles

## ✨ Features

### 🔐 Authentication System
- **Microsoft Account Login**: Secure OAuth 2.0 authentication with PKCE
- **Offline Mode**: Play without authentication for testing purposes
- **Account Management**: Save and switch between multiple accounts
- **Automatic Token Refresh**: Seamless re-authentication when tokens expire

### 📦 Modpack Management
- **Automatic Installation**: One-click setup of Minecraft, Forge, and mods
- **Update System**: Automatic detection and installation of modpack updates
- **File Integrity**: SHA-256 verification ensures file authenticity
- **Smart Updates**: Only downloads changed files to save bandwidth

### 🎨 User Interface
- **Modern Dark Theme**: Eye-friendly interface with custom styling
- **Progress Tracking**: Real-time feedback during installation and updates
- **Tabbed Interface**: Organized sections for Home, Accounts, Settings, and Logs
- **DPI Aware**: Crisp display on high-resolution screens

### ⚙️ Advanced Features
- **Memory Management**: Configurable RAM allocation (2-16 GB)
- **Game Console**: Built-in log viewer for debugging
- **Protected Files**: Preserves user settings during updates
- **Launcher Auto-Update**: Self-updating capability for bug fixes

## 🛠️ Technical Stack

- **Language**: Python 3.8+
- **GUI Framework**: Tkinter with custom ttk styling
- **Minecraft Integration**: [minecraft-launcher-lib](https://pypi.org/project/minecraft-launcher-lib/)
- **Authentication**: Microsoft Azure AD OAuth 2.0
- **HTTP Requests**: requests library
- **Image Processing**: Pillow (PIL)

## 📋 Requirements

### For Users
- Windows 10/11 (64-bit)
- 4-8 GB RAM recommended for the modpack
- Java 17 or higher (automatically detected)
- Active internet connection
- Legitimate Minecraft Java Edition account (for online play)

### For Developers
```bash
pip install minecraft-launcher-lib
pip install requests
pip install pillow
```

## 🚀 Installation

### For Users
1. Download the latest `CignoLauncher.exe` from [Releases](https://github.com/yourusername/CignoLauncher/releases)
2. Run the executable
3. Follow the on-screen instructions to install the modpack

### For Developers
1. Clone the repository:
```bash
git clone https://github.com/yourusername/CignoLauncher.git
cd CignoLauncher
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Azure App credentials in `cignolauncher.py`:
```python
self.AZURE_CLIENT_ID = "your-client-id"
self.AZURE_CLIENT_SECRET = "your-client-secret"
```

4. Run the launcher:
```bash
python cignolauncher.py
```

## 🔑 Azure App Configuration

This launcher uses Microsoft Azure Active Directory for authentication. To set up your own instance:

1. Create an Azure AD application at [Azure Portal](https://portal.azure.com)
2. Configure the redirect URI: `http://localhost:5000/callback`
3. Request Minecraft API permissions at: https://aka.ms/mce-reviewappid
4. Add your credentials to the launcher configuration

**Note**: The Azure App requires approval from Microsoft before it can authenticate Minecraft accounts. This process can take several days.

## 📁 Project Structure

```
CignoLauncher/
├── cignolauncher.py          # Main launcher application
├── account_manager.py        # Account authentication and storage
├── login_dialog.py          # Login interface and OAuth flow
├── assets/                  # Icons and images
│   ├── window_icon.ico
│   ├── home_icon.png
│   ├── account_icon.png
│   ├── settings_icon.png
│   └── log_icon.png
└── requirements.txt         # Python dependencies
```

## 🎯 How It Works

### Installation Process
1. **Minecraft Installation**: Downloads vanilla Minecraft 1.20.1
2. **Forge Installation**: Installs Forge 1.20.1-47.4.6 mod loader
3. **Modpack Download**: Fetches mods, configs, and resources from GitHub
4. **Verification**: Validates file integrity using SHA-256 hashes

### Update Mechanism
- Checks GitHub repository for manifest updates on startup
- Compares local file hashes with remote manifest
- Downloads only modified or missing files
- Preserves user settings and configurations

### Authentication Flow
1. User clicks "Login with Microsoft"
2. Browser opens with Microsoft login page
3. User authenticates and authorizes the app
4. Launcher receives authorization code via local HTTP server
5. Exchanges code for access token using Azure credentials
6. Stores encrypted tokens for future sessions

## 🔒 Security & Privacy

- **No Password Storage**: Uses OAuth 2.0, never stores user passwords
- **PKCE Protection**: Implements Proof Key for Code Exchange for additional security
- **Local Token Storage**: Access tokens stored locally in encrypted format
- **Minimal Permissions**: Only requests necessary Minecraft API access
- **Open Source**: All code is public and auditable

## 🐛 Known Issues

- Azure App requires Microsoft approval for Minecraft API access
- First-time installation may take 5-10 minutes depending on connection speed
- Some antivirus software may flag the executable (false positive)

## 📝 License

This project is for **educational purposes only**. 

**Important**: 
- Minecraft® is a trademark of Mojang Studios
- This launcher requires legitimate Minecraft ownership
- Not affiliated with or endorsed by Mojang Studios or Microsoft
- Users must comply with Minecraft's EULA and Terms of Service

## 🤝 Contributing

This is primarily an educational project, but suggestions and improvements are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Open a Pull Request

## 📧 Contact

For questions about this educational project, please open an issue on GitHub.

---

**Disclaimer**: This launcher is a student project created for educational purposes to demonstrate software development skills. It is not intended for commercial use or wide distribution. All users must own a legitimate copy of Minecraft Java Edition to use this launcher for online play.

## 🙏 Acknowledgments

- [minecraft-launcher-lib](https://minecraft-launcher-lib.readthedocs.io/) - Core Minecraft integration
- Microsoft Azure - Authentication platform
- Mojang Studios - Minecraft game
- Python Community - Excellent documentation and support

---

**Made with ❤️ as a school project to learn software development**

# VisionMD Electron
This repository holds the source code for the frontend and the full releases of VisionMD Electron. Below is the documentation for developing, building and deploying the VisionMD Desktop app.


## Development
Follow the below steps to get the app running for development.

### 1. Install Libraries
```bash
npm install
```
This will install all the required node modules from the `package.json` file.

### 2. Run the backend server
The backend server is a Django server that can be found at https://github.com/mea-lab/VisionMD-DesktopApp-BackEnd. Follow the instructions from the above repository and run it for development and testing. You must have the backend Django server running on `127.0.0.1:8000`.

### 3. Run the frontend server
```bash
npm run dev
```
This starts the app by default on the port `5173`. It will automatically open up a window for you to view and test.


## Building for Production
Below details the steps for building the installers and packages needed for Linux, MacOS, and Windows. This assumes you already have correctly built and transfer the pyinstaller executable for the Django server according to your OS. If not, follow the instructions for building the pyinstaller executable at https://github.com/mea-lab/VisionMD-DesktopApp-BackEnd.

### Building static web assets for internal testing
This section documents building the static web assets for internal testing on the backend repository of https://github.com/mea-lab/VisionMD-DesktopApp-BackEnd. This option allows for faster builds and testing to get quick feedback. 

```bash
npm run build
```

This will build static web assets at `./out/renderer`. Transfer the `renderer` directory to the root of the https://github.com/mea-lab/VisionMD-DesktopApp-BackEnd repository. Rename it to `dist`. Follow the README in the backend repository to set up the backend server and test your static web assets.

### Windows
```bash
npm run build:win
```

This will build an unpackaged app at `./dist/win-unpacked/VisionMD.exe` ready to be run and tested for production. There will also be an installer at `./dist/VisionMD Setup X.X.X.exe`.

### Linux
```bash
npm run build:linux
```
This will build an unpackaged app at `./dist/linux-unpacked/visionmd` ready to be run and tested for production. There will also be `.deb`, `.AppImage` and `.snap` packages at `./dist/visionmd_X.X.X.{ext}` for installation.

### MacOS
```bash
./mac_config/build_mac_container.sh
npm run build:mac:mas # For production
npm run build:mac:mas-dev # For sandbox testing
```

In order to build the `.pkg` file for Mac Apple Store (MAS) submission, you will need the Apple Distribution Certificate and the latest provision profile to pass the code signing steps. Contact Dr. Guarin for this information. 

If you are building for sandbox testing, you will need the Apple Developement Certificate and the latest developement provision profile to pass the code signing steps. Once again, Contact Dr. Guarin for this information. 
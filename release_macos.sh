#!/bin/zsh

VENV="venv"
LOGLEVEL="WARN"  # TRACE, DEBUG, INFO, WARN, DEPRECATION, ERROR, FATAL
STYLE_ON="\033[1;36m"
STYLE_OFF="\033[0m"

echo $STYLE_ON
echo "Running Printrun build script..."
if [ ! -d $VENV ]; then
  echo "Creating a Python virtual environment named $VENV..."
  python3 -m venv $VENV
fi

echo "Activating a Python virtual environment named $VENV..."
. $VENV/bin/activate

echo "Installing dependencies..."
echo $STYLE_OFF
pip install --upgrade pip
pip install -r requirements.txt --upgrade
pip install setuptools cython pyinstaller --upgrade
python setup.py build_ext --inplace

echo $STYLE_ON
echo "Writing pyinstaller specification..."
echo $STYLE_OFF
rm -rf dist

echo $STYLE_ON
echo "Collecting current printrun version..."
echo $STYLE_OFF
GIT_HASH=$(git rev-parse --short HEAD)
VERSION="$(python3 -c 'import printrun.printcore as core; print(core.__version__)' 2>/dev/null)"
YEAR=$(date +%Y)
echo "Printrun version: $VERSION"

pyi-makespec --windowed --name "Pronterface" \
	--add-data "printrun/assets:printrun/assets" \
	--icon "./assets_raw/icons/pronterface.icns" pronterface.py

sed -i '' '$ s/.$//' Pronterface.spec
cat >> Pronterface.spec <<EOL
info_plist={
    'CFBundleVersion': '$GIT_HASH',
    'CFBundleShortVersionString': "$VERSION",
    'NSHumanReadableCopyright': "FOSS © $YEAR, GPL-3.0 licensed",
    'NSPrincipalClass': 'NSApplication',
    'NSAppleScriptEnabled': False,
    'NSAppSleepDisabled': True,
  },
)
EOL

pyi-makespec --console --onefile --name "Pronsole" \
	--icon "./assets_raw/icons/pronsole.icns" pronsole.py

sed -i '' '$ s/.$//' Pronsole.spec
cat >> Pronsole.spec <<EOL
info_plist={
    'CFBundleVersion': '$GIT_HASH',
    'CFBundleShortVersionString': "$VERSION",
    'NSHumanReadableCopyright': "FOSS © $YEAR, GPL-3.0 licensed",
    'NSPrincipalClass': 'NSApplication',
    'NSAppleScriptEnabled': False,
    'NSAppSleepDisabled': True,
  },
)
EOL

pyi-makespec --windowed --name "Plater" \
	--add-data "printrun/assets:printrun/assets" \
	--icon "./assets_raw/icons/plater.icns" plater.py

sed -i '' '$ s/.$//' Plater.spec
cat >> Plater.spec <<EOL
info_plist={
    'CFBundleVersion': '$GIT_HASH',
    'CFBundleShortVersionString': "$VERSION",
    'NSHumanReadableCopyright': "FOSS © $YEAR, GPL-3.0 licensed",
    'NSPrincipalClass': 'NSApplication',
    'NSAppleScriptEnabled': False,
    'NSAppSleepDisabled': True,
  },
)
EOL

echo $STYLE_ON
echo "Building applications..."
echo "Building Pronterface..."
echo $STYLE_OFF
pyinstaller --log-level=$LOGLEVEL --clean Pronterface.spec -y
echo $STYLE_ON
echo "Building Pronsole..."
echo $STYLE_OFF
pyinstaller --log-level=$LOGLEVEL --clean Pronsole.spec -y
echo $STYLE_ON
echo "Building Plater..."
echo $STYLE_OFF
pyinstaller --log-level=$LOGLEVEL --clean Plater.spec -y
echo $STYLE_ON
echo "Build script has finished."
echo $STYLE_OFF


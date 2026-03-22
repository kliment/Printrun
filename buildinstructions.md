# Build instructions
In general please follow the build instructions as described in [README.md](README.md). Here you will find a brief overview about what is needed to build your own development environment without further explanations.

## Setup on macOS
### Prerequisites
* install supported python version (see [README.md](README.md))
* install python extension compile environment, this is automatically done if you have xcode
* install git
### Clone the repository
```
git clone http://github.com/kliment/Printrun.git
cd Printrun
git pull
```
### Install and activate the virtual environment
```
python3 -m venv venv
. ./venv/bin/activate
```
### Install and update all required libraries
```
pip install --upgrade pip
pip install --upgrade setuptools
pip install -r requirements.txt
pip install cython
python setup.py build_ext --inplace
```

### For running
`python pronterface.py`

### For packaging
Please find further informations about building a development environment and packaging in the script [release_macos.sh](release_macos.sh) where we implemented an automated build for macOS.

## Setup on Windows
### Prerequisites
* install supported python version (see [README.md](README.md))
* install python extension compile environment, see https://wiki.python.org/moin/WindowsCompilers
* install git
### Clone the repository
```
git clone http://github.com/kliment/Printrun.git
cd Printrun
git pull
```
### Install and activate the virtual environment
```
\path\to\python3\python -m venv v3
v3\Scripts\activate
### Install and update all required libraries
pip install --upgrade pip
pip install --upgrade setuptools
pip install wheel
pip install cython
pip install -r requirements.txt
pip install simplejson
pip install pypiwin32
pip install polygon3
python setup.py build_ext --inplace
```

Please see remark for polygon3[^1]

### For running
`python pronterface.py`

### For packaging
Please find further informations about building a development environment and packaging in the script [release_windows.bat](release_windows.bat) where we implemented an automated build for windows.

### Remark:

[^1]: The library **polygon3** is free for non commercial use. You can build Pronterface without this library - but then it will run slower.
  Please find further details regarding license here: https://pypi.org/project/Polygon3/


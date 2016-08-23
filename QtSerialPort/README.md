Mac OS X build system

1. Install homebrew `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
1. `brew install qt5`
1. `brew link --force qt5` to put qmake for qt5 on the path
1. `brew cask install qt-creator`
1. `launchctl setenv QTDIR /usr/local/Cellar/qt5/5.6.0/`
    * Modify above directory to match your version of qt5
    * This is only temporary. You'll have to find your own method to make this environment variable permanent.
    * Might be necessary to `PATH="/usr/local/opt/qt5/bin:$PATH"`
1. From the Applications menu, launch QT Creator.
1. You'll have to configure a "Kit" (i.e., a build system). Choose the compiler and debugger. For Qt, browse to the desired qmake file.
1. Configure the project.

Windows 10 build system

1. Install Qt 5.6.X from Qt download page `https://www.qt.io/download-open-source/#section-2`
   You can download Qt Online Installers to install Qt 5.6.X. or
   If you installed Visual Studio 2013/2015 on your PC, please select the corresponding Qt version(For example: `Qt 5.6.1-1 for Windows 64-bit (VS 2015, 832 MB)` if you have `VS 2015 -64 bits` )
   `Visual Studio 2012` or `earlier` version is not available.
2. Copy `..\Qt\Qt5.6.X\5.6\msvc20XX\bin` into your system variable path
   Modify above directory to match your version of Qt5
3. Open Qt Creator and import the project
4. This project is compiled by `Microsoft Visual C++ Compiler 14.0`, you could have to change the compiler by manually       setting `Tools -> Options -> Build&Run -> Compiler` in Qt Creator
5. Configure the project
5. You can see .pro file in `Project View` in Qt Creator and look through its content
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

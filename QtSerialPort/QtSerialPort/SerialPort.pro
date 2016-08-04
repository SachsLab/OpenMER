#-------------------------------------------------
#
# Project created by QtCreator 2016-06-01T18:53:12
#
#-------------------------------------------------

QT       += core gui
QT       += serialport

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = SerialPort
TEMPLATE = app


SOURCES += main.cpp\
        mainwindow.cpp

HEADERS  += mainwindow.h

FORMS    += mainwindow.ui

win32:CONFIG(release, debug|release): LIBS += -L$$PWD/../../thirdparty/cbsdk/lib/ -lcbsdk
else:win32:CONFIG(debug, debug|release): LIBS += -L$$PWD/../../thirdparty/cbsdk/lib/ -lcbsdkd
else:unix: LIBS += -L$$PWD/../../thirdparty/cbsdk/lib/ -lcbsdk

INCLUDEPATH += $$PWD/../../thirdparty/cbsdk/include
DEPENDPATH += $$PWD/../../thirdparty/cbsdk/include

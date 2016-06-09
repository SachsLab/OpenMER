#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QDebug>
#include <QSerialPort>
#include <QSerialPortInfo>
#include <QTextCodec>
#include <QString>

namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:

    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

    QByteArray data_received;//save receiving data
    QTextCodec *tc = QTextCodec::codecForName("GBK");//text encoding

private slots:
    void ReadMyCom();
    void reset_serialPort();

private:
    Ui::MainWindow *ui;
    QString showString;
    QSerialPort *mSerialPort;//declare serial object
    QSerialPortInfo *mSerialPortInfo;//declare serialinfo object
};

#endif // MAINWINDOW_H

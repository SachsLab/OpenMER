#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QSerialPortInfo>
#include <QDebug>
#include <QSerialPort>
#include <QTextCodec>

namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

    QByteArray data_received;//用于缓存从串口读取的数据
    QByteArray data_send;//用于保存即将发送的数据

    QTextCodec *tc = QTextCodec::codecForName("GBK");//编码格式
private slots:
    void ReadMyCom();//定义槽函数


    void on_pushButton_open_clicked();

    void on_pushButton_close_clicked();

    void on_pushButton_send_clicked();

    void on_pushButton_clicked();

    void on_textBrowserRefesh();

private:
    Ui::MainWindow *ui;
    QSerialPort *mSerialPort;//声明serial对象
    QSerialPortInfo *mSerialPortInfo;//声明serialinfo对象
};

#endif // MAINWINDOW_H

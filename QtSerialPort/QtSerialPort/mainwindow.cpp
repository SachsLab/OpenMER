#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QMessageBox>
#include <QLabel>
//#include <QFont>
#include <QString>
#include <QByteArray>
#include <iostream>

using namespace std;

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    mSerialPort = new QSerialPort;
    mSerialPortInfo = new QSerialPortInfo;
    //Connect QIODevice readyRead signal to our ReadMyCom: http://doc.qt.io/qt-5/qiodevice.html#readyRead
    connect(mSerialPort, SIGNAL(readyRead()), this, SLOT(ReadMyCom()));
    // Changing comboBox value triggers our reset_serialPort()
    connect(ui->comboBox, SIGNAL(currentIndexChanged(int)), this, SLOT(reset_serialPort()));

    QList<QSerialPortInfo> comInfoList = mSerialPortInfo->availablePorts();//get serial port list information
    if(comInfoList.isEmpty())//no serial port can be used
    {
        QMessageBox::warning(this,"Waring!","There's no avalible COM to use, plese check your serialport!");
    }
    else//show available port
    {
        for(int i = 0; i < comInfoList.size(); i ++)
        {
            ui->comboBox->addItem(comInfoList[i].portName());
        }
    }

    reset_serialPort();
}

MainWindow::~MainWindow()
{
    mSerialPort->close();
    delete ui;
}

void MainWindow::reset_serialPort()
{
    if (mSerialPort->isOpen())
    {
        mSerialPort->close();
    }

    try{

        //mSerialPort->setPort(comInfoList.first());
        mSerialPort->setPortName(ui->comboBox->currentText());//set serial port
        mSerialPort->open(QIODevice::ReadWrite);// open this serial port
        mSerialPort->setBaudRate(19200);
        mSerialPort->setDataBits(QSerialPort::Data8);
        mSerialPort->setFlowControl(QSerialPort::NoFlowControl);
        mSerialPort->setStopBits(QSerialPort::OneStop);
        mSerialPort->setParity(QSerialPort::NoParity);

        //data_received = mSerialPort->readLine();//read data from serial port
       // QString str = tc->toUnicode(data_received);//change format of received data
        //double a = str.toDouble();
        //double b = -29.456;
        //QString c = "-29.0";
        /*QwtText qText = str;
        QFont qfont = qText.font();
        qfont.setBold(true);
        qfont.setPointSize(40);
        qText.setFont(qfont);*/

        //ui->textBrowser->insertPlainText(str);//show received data
       // ui->lcdNumber->setDigitCount(7);
        //ui->lcdNumber->display(str.trimmed());//double number
    }
    catch(...){
        QMessageBox::warning(this,"ERROR!","Cannot open the serialport!");
    }

}

void MainWindow::ReadMyCom()
{
    if(mSerialPort->waitForReadyRead(50)){
    data_received = mSerialPort->readAll();//read data from serial port
    }
    //QString str = tc->toUnicode(data_received);
    showString.append(data_received);

    ui->lcdNumber->setDigitCount(7);
    ui->lcdNumber->display(showString);//double number
    //ui->textBrowser->insertPlainText(str);
}

void MainWindow::on_pushButton_clicked()
{
    //QByteArray send_data = ui->lineEdit->text();
    //mSerialPort->write(ui->lineEdit->text());
    mSerialPort->write(ui->lineEdit->text().toLatin1()+ "\n");
    //mSerialPort->write(send_data + "\n");//send data
    ui->lineEdit->clear();
}

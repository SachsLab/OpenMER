#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QMessageBox>
#include <QLabel>
//#include <QFont>
#include <QString>
#include <QByteArray>
#include <iostream>
#include <string>
#include <sstream>
#include <iomanip>
#define NO_AFX
#include "cbsdk.h"

using namespace std;

#define INST 0
#define SENDTIMEOUT 4000

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    mSerialPort = new QSerialPort;
    mSerialPortInfo = new QSerialPortInfo;
    //Connect QIODevice readyRead signal to our ReadMyCom: http://doc.qt.io/qt-5/qiodevice.html#readyRead
    connect(mSerialPort, SIGNAL(readyRead()), this, SLOT(ReadMyCom()));
    //connect(mSerialPort, SIGNAL(readyRead()), this, SLOT(on_pushButton_clicked()));
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
    myTime.start();
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
    //char buffer[7];
    if(mSerialPort->waitForReadyRead(50)){
    data_received = mSerialPort->readLine();//read data from serial port

    }
    //QString str = data_received;

    //std::cout<<data_received<<endl;
    //showString.append(data_received);
    double nb = data_received.toDouble();

    if(nb != 0)
    {
        //std::cout<<std::setprecision(5)<<nb<<endl;
        ui->lcdNumber->setDigitCount(7);
        ui->lcdNumber->display(QString::number(nb,'f',3));//double number
        //ui->textBrowser->insertPlainText(str);

        if((nb != a) || (myTime.elapsed() > SENDTIMEOUT))
        {
            std::ostringstream strs;
            strs << nb << endl;
            std::string str = strs.str();
            str.insert(0,"DTT: ");
            const char* sds = str.c_str();

            if(strlen(sds)!=13)
                str.insert(12,"0");

            cbSdkResult res = cbSdkSetComment(INST, 255, 1, sds);
            cout<<sds<<endl;
            if (res > 0)
            {
                ui->lineEdit->setPlaceholderText("Cannot communicate with NSP!");
            }else
            {
                ui->lineEdit->setPlaceholderText("the deepth measurement is sending to NSP!");
            }
            a = nb;
            myTime.restart();
        }
    }
}

void MainWindow::on_pushButton_clicked()
{

//    if(mSerialPort->isOpen())
//    {

//       // if(mSerialPort->waitForReadyRead(50)){
//        data_received = mSerialPort->readLine();//read data from serial port
//        cout<<"jhkhkj"<<endl;
//        //}

//        double nb = data_received.toDouble();
//        if(nb != 0)
//        {
//            std::cout<<std::setprecision(5)<<nb<<endl;
//            cout<<"ssfsfdfsd"<<endl;
//            //const char* a = ConvertDoubleToString(nb);
//            cbSdkResult res = cbSdkSetComment(INST, 255, 1, "test");
//            if (res > 0)
//            {
//                ui->lineEdit->setPlaceholderText("Cannot communicate with NSP!");
//            }else
//            {
//                ui->lineEdit->setPlaceholderText("the deepth measurement is sending to NSP!");
//            }
//        }
//    }
//    ui->lineEdit->setPlaceholderText("the deepth measurement is sending to NSP!");
}


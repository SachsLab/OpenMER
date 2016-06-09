#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QMessageBox>


MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    //串口对象实例化
    mSerialPort = new QSerialPort;
    mSerialPortInfo = new QSerialPortInfo;
    //将信号与槽连接起来
    connect(mSerialPort,SIGNAL(readyRead()),this,SLOT(ReadMyCom()));
    connect(ui->textBrowser,SIGNAL(textChanged()),this,SLOT(on_textBrowserRefesh()));

    ui->pushButton_close->setDisabled(true);//开始讲“关闭”按钮设置为无效
    ui->pushButton_send->setDisabled(true);//开始讲“发送”按钮设置为无效

    QList<QSerialPortInfo> comInfoList = mSerialPortInfo->availablePorts();//获取可用串口列表
    if(comInfoList.isEmpty())//若没有可用串口，则发送警告
    {
        QMessageBox::warning(this,"Waring!","There's no avalible COM to use, plese check your serialport!");
    }
    else//将可用串口显示到comboBox上以供选择
    {
        for(int i = 0; i < comInfoList.size(); i ++)
        {
            ui->comboBox_portName->addItem(comInfoList[i].portName());
        }
    }
    QStringList baudRateList = QStringList() << "1200" << "2400" << "4800"
                                             << "9600" << "14400" << "19200" << "38400" << "43000" << "57600"
                                             << "76800" << "115200" << "128000" << "230400" << "256000" <<"460800"
                                             << "921600" << "1382400";
    QStringList parityList = QStringList() << "无" << "奇校验" << "偶校验";
    QStringList stopBitsList = QStringList() << "1" << "1.5" << "2";
    QStringList dataBitsList = QStringList() << "8" << "7" << "6" << "5";

    ui->comboBox_baudRate->addItems(baudRateList);
    ui->comboBox_baudRate->setCurrentIndex(3);//设置9600为默认选项

    ui->comboBox_parity->addItems(parityList);
    ui->comboBox_stopBit->addItems(stopBitsList);
    ui->comboBox_dataBit->addItems(dataBitsList);

  /*  mSerialPort->setPort(comInfoList.first());
    mSerialPort->open(QIODevice::ReadWrite);
    mSerialPort->setBaudRate(115200);
    mSerialPort->setDataBits(QSerialPort::Data8);
    mSerialPort->setFlowControl(QSerialPort::NoFlowControl);
    mSerialPort->setStopBits(QSerialPort::OneStop);
    mSerialPort->setParity(QSerialPort::NoParity);*/


}

MainWindow::~MainWindow()
{
    mSerialPort->close();//在关闭窗体时关闭串口
    delete ui;
}

void MainWindow::ReadMyCom()
{
    data_received = mSerialPort->readAll();//读取串口上所有数据
    QString str = tc->toUnicode(data_received);//将接受到的数据改变编码格式
    ui->textBrowser->insertPlainText(str);//显示接收到的数据

}

void MainWindow::on_textBrowserRefesh()
{
    ui->textBrowser->moveCursor(QTextCursor::End);//设置每次接收到新数据时光标跟随移动
}

void MainWindow::on_pushButton_open_clicked()
{
    try
    {
        mSerialPort->setPortName(ui->comboBox_portName->currentText());//设置串口
        mSerialPort->open(QIODevice::ReadWrite);//打开串口
        mSerialPort->setBaudRate(ui->comboBox_baudRate->currentText().toInt());//设置波特率

        QString currentData = " ";//用于保存将要发送的数据
        currentData = ui->comboBox_dataBit->currentText();//读取textedit上的数据
        switch(currentData.toInt())
        {
            case 8:mSerialPort->setDataBits(QSerialPort::Data8);break;
            case 7:mSerialPort->setDataBits(QSerialPort::Data7);break;
            case 6:mSerialPort->setDataBits(QSerialPort::Data6);break;
            case 5:mSerialPort->setDataBits(QSerialPort::Data5);break;
        }
        mSerialPort->setFlowControl(QSerialPort::NoFlowControl);
        currentData = ui->comboBox_stopBit->currentText();
        int n = ui->comboBox_stopBit->currentIndex();
        switch(n)
        {
            case 0:mSerialPort->setStopBits(QSerialPort::OneStop);break;
            case 1:mSerialPort->setStopBits(QSerialPort::OneAndHalfStop);break;
            case 2:mSerialPort->setStopBits(QSerialPort::TwoStop);break;

        }
        int m = ui->comboBox_parity->currentIndex();
        switch(m)
        {
            case 0:mSerialPort->setParity(QSerialPort::NoParity);break;
            case 1:mSerialPort->setParity(QSerialPort::EvenParity);break;
            case 2:mSerialPort->setParity(QSerialPort::OddParity);break;

        }
        ui->pushButton_close->setDisabled(false);
        ui->pushButton_send->setDisabled(false);
        ui->pushButton_open->setDisabled(true);
    }
    catch(...)
    {
        QMessageBox::warning(this,"ERROR!","Cannot open the serialport!");
    }

}

void MainWindow::on_pushButton_close_clicked()//当打开串口后，使能关闭按钮和发送按钮，失能打开按钮
{
    mSerialPort->close();

    ui->pushButton_close->setDisabled(true);
    ui->pushButton_open->setDisabled(false);
    ui->pushButton_send->setDisabled(true);
}

void MainWindow::on_pushButton_send_clicked()
{
    mSerialPort->write(ui->lineEdit_send->text().toLatin1());//发送串口数据
}

void MainWindow::on_pushButton_clicked()
{
    ui->textBrowser->clear();//清屏
}

#include "mainwindow.h"
#include "ui_mainwindow.h"
#include "BStimulator.h"

#include <iostream>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    // TODO: create cerestim object.
}

MainWindow::~MainWindow()
{
    // TODO: tear down cerestim object.

    delete ui;
}

void MainWindow::on_deviceRefreshPushButton_clicked()
{
    ui->deviceComboBox->clear();
    std::vector<uint32_t> deviceSerials;
    /*
    BResult scanResult = BStimulator::scanForDevices(deviceSerials);
    for(std::vector<uint32_t>::iterator it = deviceSerials.begin(); it != device_serial_nums.end(); ++it) {
        std::cout << *it << std::endl;
    }
    */
    ui->deviceConnectPushButton->setEnabled(true);
    // TODO: Set combo box to first item.
    // TODO: Enable deviceConnectPushButton.
}

void MainWindow::on_deviceConnectPushButton_clicked()
{
    if (m_stimulator.isConnected())
    {
        m_stimulator.disconnect();
        // TODO: Change text on deviceConnectPushButton to 'connect'.
    }
    else
    {
        // TODO: Get currently selected device from combo box.
        uint32_t deviceIndex = 1;
        BResult setResult = m_stimulator.setDevice(deviceIndex);
        //std::cout << "setResult: " << setResult << std::endl;
        BResult connectResult = m_stimulator.connect(BINTERFACE_DEFAULT, 0);
        std::cout << "connectResult: " << connectResult << std::endl;
        // TODO: Change text on deviceConnectPushButton to 'disconnect'.
    }

}

void MainWindow::on_stimGenPushButton_clicked()
{
    // TODO: Collect information from GUI.
    // TODO: Calculate waveforms.
    // TODO: Indicate waveform calculation success.
    // TODO: Send waveforms to stimulator.
    // TODO: Enable Stimulate! button.
}

void MainWindow::on_stimulatePushButton_clicked()
{
    // TODO: Change text to "Stop!"
    // TODO: Stimulate!
}

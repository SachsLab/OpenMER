#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include "BStimulator.h"

namespace Ui {
class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

private slots:
    void on_deviceRefreshPushButton_clicked();

    void on_deviceConnectPushButton_clicked();

    void on_stimGenPushButton_clicked();

    void on_stimulatePushButton_clicked();

private:
    Ui::MainWindow *ui;
    BStimulator m_stimulator;
};

#endif // MAINWINDOW_H

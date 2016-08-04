#include "mainwindow.h"
#include <QApplication>
#include <QTextCodec>
#include <map>
#include <string>
#include <vector>
#include <stdio.h>
#include <iostream>
#include <QtSerialPort>
#include <QtCore>
#include <QIODevice>
#include <iomanip>
#include <QObject>
#include <QByteArray>
#include <QString>
#define NO_AFX
#include "cbsdk.h"

using namespace std;


#define INST 0


cbSdkResult testOpen(void)
{
    cbSdkConnectionType conType = CBSDKCONNECTION_DEFAULT;// = 0

    // Library version can be read even before library open (return value is a warning)
    //  actual NSP version however needs library to be open
    cbSdkVersion ver;
    cbSdkResult res = cbSdkGetVersion(INST, &ver);

    printf("Initializing Cerebus real-time interface %d.%02d.%02d.%02d (protocol cb%d.%02d)...\n", ver.major, ver.minor, ver.release, ver.beta, ver.majorp, ver.minorp);
    //std::cout<< "NSP information:" << ver.nspmajor << " " << ver.nspminor << " " << ver.nsprelease << " " << ver.nspbeta << " " << ver.nspmajorp << " " << ver.nspminorp <<std::endl;

    cbSdkInstrumentType instType;
    res = cbSdkOpen(INST, conType);
    switch (res)
    {
    case CBSDKRESULT_SUCCESS:
        break;
    case CBSDKRESULT_NOTIMPLEMENTED:
        printf("Not implemented\n");
        break;
    case CBSDKRESULT_INVALIDPARAM:
        printf("Invalid parameter\n");
        break;
    case CBSDKRESULT_WARNOPEN:
        printf("Real-time interface already initialized\n");
    case CBSDKRESULT_ERROPENCENTRAL:
        printf("Unable to open library for Central interface\n");
        break;
    case CBSDKRESULT_ERROPENUDP:
        printf("Unable to open library for UDP interface\n");
        break;
    case CBSDKRESULT_ERROPENUDPPORT:
        res = cbSdkGetType(INST, NULL, &instType);
        if (instType == CBSDKINSTRUMENT_NPLAY || instType == CBSDKINSTRUMENT_REMOTENPLAY)
            printf("Unable to open UDP interface to nPlay\n");
        else
            printf("Unable to open UDP interface\n");
        break;
    case CBSDKRESULT_OPTERRUDP:
        printf("Unable to set UDP interface option\n");
        break;
    case CBSDKRESULT_MEMERRUDP:
        printf("Unable to assign UDP interface memory\n"
            " Consider using sysctl -w net.core.rmem_max=8388608\n"
            " or sysctl -w kern.ipc.maxsockbuf=8388608\n");
        break;
    case CBSDKRESULT_INVALIDINST:
        printf("Invalid UDP interface\n");
        break;
    case CBSDKRESULT_ERRMEMORYTRIAL:
        printf("Unable to allocate RAM for trial cache data\n");
        break;
    case CBSDKRESULT_ERROPENUDPTHREAD:
        printf("Unable to Create UDP thread\n");
        break;
    case CBSDKRESULT_ERROPENCENTRALTHREAD:
        printf("Unable to start Cerebus real-time data thread\n");
        break;
    case CBSDKRESULT_ERRINIT:
        printf("Library initialization error\n");
        break;
    case CBSDKRESULT_ERRMEMORY:
        printf("Library memory allocation error\n");
        break;
    case CBSDKRESULT_TIMEOUT:
        printf("Connection timeout error\n");
        break;
    case CBSDKRESULT_ERROFFLINE:
        printf("Instrument is offline\n");
        break;
    default:
        printf("Unexpected error\n");
        break;
    }

    if (res >= 0)
    {
        // Return the actual openned connection
        res = cbSdkGetType(INST, &conType, &instType);
        if (res != CBSDKRESULT_SUCCESS)
            printf("Unable to determine connection type\n");
        res = cbSdkGetVersion(INST, &ver);
        if (res != CBSDKRESULT_SUCCESS)
            printf("Unable to determine instrument version\n");

        if (conType < 0 || conType > CBSDKCONNECTION_CLOSED)
            conType = CBSDKCONNECTION_COUNT;
        if (instType < 0 || instType > CBSDKINSTRUMENT_COUNT)
            instType = CBSDKINSTRUMENT_COUNT;

        char strConnection[CBSDKCONNECTION_COUNT + 1][8] = {"Default", "Central", "Udp", "Closed", "Unknown"};
        char strInstrument[CBSDKINSTRUMENT_COUNT + 1][13] = {"NSP", "nPlay", "Local NSP", "Remote nPlay", "Unknown"};
        printf("%s real-time interface to %s (%d.%02d.%02d.%02d) successfully initialized\n", strConnection[conType], strInstrument[instType], ver.nspmajor, ver.nspminor, ver.nsprelease, ver.nspbeta);
    }

    //res = cbSdkSetComment(INST, 255, 1, "Da test comment");

    return res;
}


cbSdkResult sendComment(void)
{
    cbSdkResult res = cbSdkSetComment(INST, 255, 1, " ");
    return res;
}

// Author & Date:   Ehsan Azar    25 Oct 2012
// Purpose: Test closing the library
cbSdkResult testClose(void)
{
    cbSdkResult res = cbSdkClose(INST);
    switch(res)
    {
    case CBSDKRESULT_SUCCESS:
        printf("Interface closed successfully\n");
        break;
    case CBSDKRESULT_WARNCLOSED:
        printf("Real-time interface already closed\n");
        break;
    default:
        printf("Unexpected error in closing the library!\n");
        break;
    }

    return res;
}


int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    cbSdkResult res = testOpen();

    if (res < 0)
        printf("testOpen failed (%d)!\n", res);
    else
        printf("testOpen succeeded\n");

        MainWindow w;
    w.show();


    return a.exec();

}

//int main(int argc, char *argv[])
//{
//   /* cbSdkResult res = testOpen();
//    if (res < 0)
//        printf("testOpen failed (%d)!\n", res);
//    else
//        printf("testOpen succeeded\n");*/

//	std::cout << "Send deepth measurement to NSP? (Y/N)" << std::endl;
//	char n;
//	std::cin >> n;

//	if (n == 'Y')
//	{
//		cbSdkResult res = sendComment();
//		if (res > 0)
//		{
//			printf("Cannot read serial port data. error(%d)!\n", res);
//		}
//		else
//			printf("deepth measurement is sending!\n");


//	}
//	else if(n == 'N')
//	{
//		cbSdkResult res = testClose();
//		if (res < 0)
//			printf("testClose failed (%d)!\n", res);
//		else
//			printf("testClose succeeded\n");
//	}
//	else
//	{
//		std::cout << "Invalid Input!" << std::endl;
//	}

//	system("pause");
//    return 0;
//}


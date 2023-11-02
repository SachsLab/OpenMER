from open_mer.dbsgui.process import parse_ini, build_ini_paths, NSPBufferWorker


def main():
    ipc_settings, buffer_settings, feature_settings = parse_ini(build_ini_paths())

    worker = NSPBufferWorker(ipc_settings, buffer_settings)
    worker.run_forever()


if __name__ == '__main__':
    main()

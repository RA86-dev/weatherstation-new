from weather_station.index import *
import threading
import time
import os

def thread_1():
    time.sleep(259200)
    os.system('./init-weather-data.sh')
    os.system('docker restart openmeteo-api')
    print(f'Finished Check!')
    return

def thread_main():
    main()
    return
if __name__ == "__main__":
    thread_0 = threading.Thread(target=thread_main, daemon=True)
    thread_0.start()
    thread_1 = threading.Thread(target=thread_1, daemon=True)
    thread_1.start()
    
    thread_0.join()
    thread_1.join()
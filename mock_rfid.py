from pirc522 import RFID
import signal
import time

rdr = RFID()
util = rdr.util()
util.debug = False

print("Scan a card (press Ctrl+C to quit)")
try:
    while True:
        rdr.wait_for_tag()
        (error, tag_type) = rdr.request()
        if not error:
            print("Card detected")
            (error, uid) = rdr.anticoll()
            if not error:
                print("UID: " + "-".join([str(x) for x in uid]))
                time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
    rdr.cleanup()

from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

reader = SimpleMFRC522()

try:
    print("Hold a tag near the reader")
    id, text = reader.read()
    print("UID:", id)
    print("Text:", text)
finally:
    GPIO.cleanup()

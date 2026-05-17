from tester.serial_comm import SerialComm

print(SerialComm.list_ports())
with SerialComm('/dev/ttyACM0') as s:
    tests = ["PING","LED_ON","LED_OFF", "GARBAGE"]
    for i in tests:
        response = s.send(i)
        print(f"  {i:10} -> {response}")
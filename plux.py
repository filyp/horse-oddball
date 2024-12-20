# %%
import plux, datetime
import socket


class MyDevice(plux.MemoryDev):

    lastSeq = 0

    def onRawFrame(self, nSeq, data):
        # soc.send('%d:%d:%d:%d:%d\r\n' % (nSeq, data[0], data[1], data[2], data[3]))
        print(nSeq, data)

        if nSeq % 10000 == 0:
            print(nSeq, data)
        if nSeq - self.lastSeq > 1:
            print('ZGUBIONE FREJMY:', nSeq - self.lastSeq)
        self.lastSeq = nSeq
        return False

    def onEvent(self, event):
        if type(event) == plux.Event.DigInUpdate:
            print('Digital input event - Clock source:', event.timestamp.source,
                  ' Clock value:', event.timestamp.value, ' New input state:', event.state)
        elif type(event) == plux.Event.SchedChange:
            print('Schedule change event - Action:', event.action,
                  ' Schedule start time:', event.schedStartTime)
        elif type(event) == plux.Event.Sync:
            print('Sync event:')
            for tstamp in event.timestamps:
                print(' Clock source:', tstamp.source, ' Clock value:', tstamp.value)
        elif type(event) == plux.Event.Disconnect:
            print('Disconnect event - Reason:', event.reason)
            return True
        return False
        
    def onInterrupt(self, param):
        print('Interrupt:', param)
        return False

    def onTimeout(self):
        print('Timeout')
        return False


# print("Found devices: ", plux.BaseDev.findDevices())
dev = None
try:
    BUFFER_SIZE = 1024
    print("connected")

    #dev = MyDevice("00:07:80:0F:2F:EF")    # MAC address of device
    dev = MyDevice("00:07:80:58:9B:B4")    # MAC address of device
    props = dev.getProperties()
    print('Properties:', props)
    dev.start(1000, 15, 16)   # 1000 Hz, ports 1-8, 16 bits
    dev.loop()
    dev.stop()
    dev.close()
finally:
    if (dev):
        dev.close()

# %%

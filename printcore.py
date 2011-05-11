from serial import Serial
from threading import Thread
import time

class printcore():
    def __init__(self,port=None,baud=None):
        """Initializes a printcore instance. Pass the port and baud rate to connect immediately
        """
        self.baud=None
        self.port=None
        self.printer=None
        self.clear=0
        self.mainqueue=[]
        self.priqueue=[]
        if port is not None and baud is not None:
            #print port, baud
            self.connect(port, baud)
            #print "connected\n"
        self.readthread=None
        self.queueindex=0
        self.lineno=0
        self.resendfrom=-1
        self.online=False
        self.printing=False
        self.sentlines={}
        
    def disconnect(self):
        """Disconnects from printer and pauses the print
        """
        if(self.printer):
            self.printer.close()
        self.printer=None
        self.online=False
        self.printing=False
        
    def connect(self,port=None,baud=None):
        """Set port and baudrate if given, then connect to printer
        """
        if(self.printer):
            self.disconnect()
        if port is not None:
            self.port=port
        if baud is not None:
            self.baud=baud
        if self.port is not None and self.baud is not None:
            self.printer=Serial(self.port,self.baud,timeout=5)
            Thread(target=self._listen).start()
            
    def _listen(self):
        """This function acts on messages from the firmware
        """
        time.sleep(1)
        while(True):
            if(not self.printer or not self.printer.isOpen):
                break
            line=self.printer.readline()
            print "RECV:",line
            if(line.startswith('start')):
                self.clear=True
                self.online=True
            elif(line.startswith('ok')):
                self.clear=True
                self.resendfrom=-1
                #put temp handling here
            elif(line.startswith('Error')):
                pass
            if "Resend" in line or "rs" in line:
                toresend=int(line.replace(":"," ").split()[-1])
                self.resendfrom=toresend
                self.clear=True
            
    def _checksum(self,command):
        return reduce(lambda x,y:x^y, map(ord,command))
        
    def startprint(self,data):
        """Start a print, data is an array of gcode commands.
        returns True on success, False if already printing.
        The print queue will be replaced with the contents of the data array, the next line will be set to 0 and the firmware notified.
        Printing will then start in a parallel thread.
        """
        if(self.printing):
            return False
        self.printing=True
        self.mainqueue=[]+data
        self.lineno=0
        self.queueindex=0
        self.resendfrom=-1
        self._send("M110",-1, True)
        Thread(target=self._print).start()
        return True
        
    def pause(self):
        """Pauses the print, saving the current position.
        """
        self.printing=False
        
    def resume(self):
        """Resumes a paused print.
        """
        self.printing=True
        threading.Thread(target=self._print).start()
    
    def send(self,command):
        """Adds a command to the checksummed main command queue if printing, or sends the command immediately if not printing
        """
        
        if(self.printing):
            self.mainqueue+=[command]
        else:
            while not self.clear:
                time.sleep(0.001)
            self._send(command,self.lineno,True)
            self.lineno+=1
        
    
    def send_now(self,command):
        """Sends a command to the printer ahead of the command queue, without a checksum
        """
        if(self.printing):
            self.priqueue+=[command]
        else:
            while not self.clear:
                time.sleep(0.001)
            self._send(command)
        
    def _print(self):
        while(self.printing and self.printer):
            self._sendnext()
        
    def _sendnext(self):
        if(not self.printer):
            return
        if(self.resendfrom>-1):
            while(self.resendfrom<self.lineno):
                while not self.clear:
                    time.sleep(0.001)
                self.clear=False
                self._send(self.sentlines[self.resendfrom],self.resendfrom,False)
                self.resendfrom+=1
            self.resendfrom=-1
        for i in self.priqueue[:]:
            while not self.clear:
                time.sleep(0.001)
            self.clear=False
            self._send(i)
            del(self.preque[0])
        if(self.printing and self.queueindex<len(self.mainqueue)):
            tline=self.mainqueue[self.queueindex]
            if(not tline.startswith(';') and len(tline)>0):
                while not self.clear:
                    time.sleep(0.001)
                self.clear=False
                self._send(tline,self.lineno,True)
            self.lineno+=1
            self.queueindex+=1
        else:
            self.printing=False
            self.queueindex=0
            self.lineno=0
            self._send("M110",-1, True)
            
    def _send(self, command, lineno=0, calcchecksum=False):
        if(calcchecksum):
            prefix="N"+str(lineno)+" "+command
            command=prefix+"*"+str(self._checksum(prefix))
            self.sentlines[lineno]=command
        if(self.printer):
            print "sending: "+command+"\n"
            self.printer.write(command+"\n")

if __name__ == '__main__':
    p=printcore('/dev/ttyUSB0',115200)
    time.sleep(5)
    testdata="""G28
G1 X0 Y0
G1 X10 Y10
G1 X0 Y0
;
"""
    p.startprint(testdata.split('\n'))
    time.sleep(10)
    p.disconnect()
